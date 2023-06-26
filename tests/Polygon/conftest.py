import pytest
from brownie import Wei, config, Contract, accounts

fixtures = "token", "aToken", "qiToken", "iToken", "lenders", "whale", "amountUSD"
params = [
    pytest.param( # USDC
        "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174", # token
        "0x625E7708f30cA75bfd92586e17077590C60eb4cD", # aToken
        "", # qiToken
        "", # iToken
        ['Aave'],
        "0xF977814e90dA44bFA03b6295A0616a897441aceC", # whale
        1000000, # amount
        id="USDC Generic Lender",
    ),
]

@pytest.fixture
def router():
    yield Contract('0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff')
    
@pytest.fixture
def weth():
    yield "0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7"

# specific addresses
@pytest.fixture
def usdc(interface):
    yield interface.ERC20("0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174")

@pytest.fixture
def token(request, interface):
    yield interface.IERC20Extended(request.param)

@pytest.fixture
def aToken(request, interface):
    if request.param == '':
        yield ''
    else:
        yield interface.CErc20I(request.param)


@pytest.fixture
def qiToken(request, interface):
    if request.param == '':
        yield ''
    else:
        yield interface.CErc20I(request.param)

@pytest.fixture
def iToken(request, interface):
    if request.param == '':
        yield ''
    else:
        yield interface.CErc20I(request.param)



@pytest.fixture
def lenders(request, interface):
    yield request.param

@pytest.fixture
def whale(request, interface):
    yield accounts.at(request.param, True)

@pytest.fixture
def amountUSD(request, interface):
    yield request.param


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
def amount(token, token_price, decimals, amountUSD):
    ## todo - make generic
    price = token_price(token, decimals)
    amount = int((amountUSD / price) * (10 ** token.decimals()))
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
    gov,
    Strategy,
    router,
    weth,
    GenericAaveV3,
    Benqi,
    GenericIronBankAVAX,
    fn_isolation
):
    strategy = strategist.deploy(Strategy, vault, weth, router)
    strategy.setKeeper(keeper)
    strategy.setWithdrawalThreshold(0)
    yield strategy

@pytest.fixture
def lenderAave(
    strategist,
    strategy,
    aToken,
    GenericAaveV3,
    lenders,
    weth,
    router
):
    if 'Aave' in lenders:
        yield strategist.deploy(GenericAaveV3, strategy, weth, router, router, "Aave", True)
    else: 
        yield ''

@pytest.fixture
def lenderBenqi(
    strategist,
    strategy,
    qiToken,
    Benqi,
    lenders
):    
    if 'Benqi' in lenders:
        bqiLender = strategist.deploy(Benqi, strategy, "Benqi", qiToken)
        bqiLender.setDust(0)
        bqiLender.setDustThreshold(0)
        yield bqiLender
    else: 
        yield ''
    
@pytest.fixture
def lenderIB(
    strategist,
    strategy,
    iToken,
    GenericIronBankAVAX,
    lenders
):    
    if 'IB' in lenders:
        ib = strategist.deploy(GenericIronBankAVAX, strategy, "IB", iToken)
        ib.setDust(0)
        ib.setDustThreshold(0)
        yield ib
    else: 
        yield ''
    
    
# Function scoped isolation fixture to enable xdist.
# Snapshots the chain before each test and reverts after test completion.
@pytest.fixture(scope="function", autouse=True)
def shared_setup(fn_isolation, lenders, aToken, qiToken, iToken):
    pass

@pytest.fixture
def dust(decimals):
    yield int(10 ** (decimals - 8))

@pytest.fixture
def strategyAllLenders(
    strategy,
    gov,
    lenderAave,
    lenderBenqi,
    lenderIB,
    lenders,
    dust
):
    if 'Aave' in lenders:
        strategy.addLender(lenderAave, {'from': gov})
    if 'Benqi' in lenders:
        strategy.addLender(lenderBenqi, {'from': gov})
    if 'IB' in lenders:
        strategy.addLender(lenderIB, {'from': gov})
    assert strategy.numLenders() == len(lenders)

@pytest.fixture
def strategyAddAave(
    strategy,
    gov,
    lenderAave,
    lenders,
    dust
):
    if 'Aave' not in lenders:
        pytest.skip()
    strategy.addLender(lenderAave, {'from': gov})
    assert strategy.numLenders() == 1

@pytest.fixture
def strategyAddBenqi(
    strategy,
    gov,
    lenderBenqi,
    lenders,
    dust
):
    if 'Benqi' not in lenders:
        pytest.skip()
    strategy.addLender(lenderBenqi, {'from': gov})
    assert strategy.numLenders() == 1

@pytest.fixture
def strategyAddIB(
    strategy,
    gov,
    lenderIB,
    lenders,
    dust
):
    if 'IB' not in lenders:
        pytest.skip()
    strategy.addLender(lenderIB, {'from': gov})
    assert strategy.numLenders() == 1