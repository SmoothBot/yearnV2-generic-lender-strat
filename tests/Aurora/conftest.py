import pytest
from brownie import Wei, config, Contract, accounts, interface

fixtures = "token", "auToken", "lenders", "whale"
# https://docs.aurigami.finance/public/protocol/contract-addresses
params = [
    pytest.param( # USDC
        "0xB12BFcA5A55806AaF64E99521918A4bf0fC40802", # token
        "0x4f0d864b1ABf4B701799a0b30b57A22dFEB5917b", # auToken
        ['AURI'],
        "0x8e9fb3f2cc8b08184cb5fb7bcdc61188e80c3cb0", # whale
        id="USDC Generic Lender",
    ),
    # pytest.param( # USDT
    #     "0x4988a896b1227218e4A686fdE5EabdcAbd91571f", # token
    #     "0xaD5A2437Ff55ed7A8Cad3b797b3eC7c5a19B1c54", # auToken
    #     ['AURI'],
    #     "0xcEf6C2e20898C2604886b888552CA6CcF66933B0", # whale
    #     id="USDT Generic Lender",
    # ),
    # pytest.param( # ETH -> this must use EthCompound, test separately?
    #     "", # token
    #     "0xca9511B610bA5fc7E311FDeF9cE16050eE4449E9", # auToken
    #     ['AURI'],
    #     "", # whale
    #     id="Eth Lender",
    # ),
    # pytest.param( # WBTC
    #     "0xF4eB217Ba2454613b15dBdea6e5f22276410e89e", # token
    #     "0xCFb6b0498cb7555e7e21502E0F449bf28760Adbb", # auToken
    #     ['AURI'],
    #     "0x871ea9aF361ec1104489Ed96438319b46E5FB4c6", # whale
    #     id="WBTC Generic Lender",
    # )
]

@pytest.fixture
def router(routerAddress):
    yield interface.IUniswapV2Router02(routerAddress)

@pytest.fixture
def routerAddress():
    # Trisolaris router is not verified, and we don't know what platform will be used to trade comp (probably trisolaris)
    # TODO change with the router where there is the most liquidity for PLY token
    yield "0x2CB45Edb4517d5947aFdE3BEAbF95A582506858B"

@pytest.fixture
def weth(interface):
    yield interface.ERC20("0xC9BdeEd33CD01541e1eeD10f90519d2C06Fe3feB")
    
@pytest.fixture
def comp(interface):
    yield interface.ERC20("0x09c9d464b58d96837f8d8b6f4d9fe4ad408d3a4f")

# specific addresses
@pytest.fixture
def usdc(interface):
    yield interface.ERC20("0xB12BFcA5A55806AaF64E99521918A4bf0fC40802")

@pytest.fixture
def token(request, interface):
    yield interface.IERC20Extended(request.param)

@pytest.fixture
def auToken(request, interface):
    if request.param == '':
        yield ''
    else:
        yield request.param

@pytest.fixture
def lenders(request, interface):
    yield request.param

@pytest.fixture
def whale(request, interface):
    yield accounts.at(request.param, True)

@pytest.fixture
def gov(accounts):
    yield accounts[3]

@pytest.fixture
def rewards(gov):
    yield gov  # TODO: Add rewards contract

@pytest.fixture
def guardian(accounts):
    # YFI Whale, probably
    yield accounts[2]

@pytest.fixture
def strategist(accounts):
    # YFI Whale, probably
    yield accounts[2]

## Price utility functions
@pytest.fixture
def get_path(weth):
    def get_path(token_in, token_out):
        is_weth = token_in == weth or token_out == weth
        path = [0] * (2 if is_weth else 3)
        path[0] = token_in
        if (is_weth):
            path[1] = token_out
        else:
            path[1] = weth
            path[2] = token_out
        return path
    yield get_path

@pytest.fixture
def token_price(router, usdc, get_path):
    def token_price(token, decimals):
        if (token.address == usdc.address):
            return 1

        path = get_path(usdc, token)
        price = router.getAmountsIn(10 ** decimals, path)[0]

        # add the fee back on
        if (len(path) == 2):
            price = price * (1 - 0.002)
        else:
            price = price * (1 - 0.004)

        return price / (10 ** usdc.decimals())

    yield token_price

@pytest.fixture
def decimals(token):
    yield token.decimals()

@pytest.fixture
def amount(token, token_price, decimals):
    ## todo - make generic
    price = token_price(token, decimals)
    amount = int((100000 / price) * (10 ** token.decimals()))
    print(amount)
    yield amount

@pytest.fixture
def vault(gov, rewards, guardian, token, pm):
    Vault = pm(config["dependencies"][0]).Vault
    vault = Vault.deploy({"from": guardian})
    vault.initialize(token, gov, rewards, "", "")
    vault.setDepositLimit(2**256-1, {"from": gov})
    yield vault

@pytest.fixture
def Vault(pm):
    yield pm(config["dependencies"][0]).Vault

@pytest.fixture
def strategy(
    strategist,
    keeper,
    vault,
    weth,
    router,
    Strategy,
):
    strategy = strategist.deploy(Strategy, vault, weth, router)
    strategy.setKeeper(keeper)
    strategy.setWithdrawalThreshold(0)
    yield strategy

@pytest.fixture
def blocksPerYear():
    # 1 second average block time
    yield 60 * 60 * 24 * 365
@pytest.fixture
def lenderAURI(
    strategist,
    strategy,
    auToken,
    GenericAurigami,
    lenders,
    comp,
    weth,
    routerAddress,
    blocksPerYear
):
    if 'AURI' in lenders:
        # Parameters : [_blocksPerYear, _uniswapRouter, _weth, _comp, _name, _ignorePrinting, _usesBlocks, _cToken, _strategy]
        yield strategist.deploy(GenericAurigami, [blocksPerYear, routerAddress, weth, comp, "AURI", True, False, auToken, strategy])
    else: 
        yield ''

# Function scoped isolation fixture to enable xdist.
# Snapshots the chain before each test and reverts after test completion.
@pytest.fixture(scope="function", autouse=True)
def shared_setup(fn_isolation, lenders, auToken):
    pass

@pytest.fixture
def dust(decimals):
    yield int(10 ** (decimals - 8))

@pytest.fixture
def strategyAllLenders(
    strategy,
    gov,
    lenderAURI,
    lenders,
    dust
):
    if 'AURI' in lenders:
        # lenderAAVE.setDustThreshold(dust, {'from': gov})
        strategy.addLender(lenderAURI, {'from': gov})
    assert strategy.numLenders() == len(lenders)

@pytest.fixture
def strategyAddAURI(
    strategy,
    gov,
    lenderAURI,
    lenders,
    dust
):
    if 'AURI' not in lenders:
        pytest.skip()
    strategy.addLender(lenderAURI, {'from': gov})
    # lenderAAVE.setDustThreshold(dust, {'from': gov})
    assert strategy.numLenders() == 1

