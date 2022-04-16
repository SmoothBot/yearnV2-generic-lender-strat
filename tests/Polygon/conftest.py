import pytest
from brownie import Wei, config, Contract, accounts

fixtures = "token", "aToken", "hToken", "hGuage", "lenders", "whale"
# https://docs.hundred.finance/developers/protocol-contracts/polygon
# https://docs.aave.com/developers/deployed-contracts/v3-mainnet/polygon
params = [
    pytest.param( # USDC
        "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174", # token
        "0x1a13F4Ca1d028320A707D99520AbFefca3998b7F", # aToken
        "0x607312a5C671D0C511998171e634DE32156e69d0", # hToken
        "0xB11C769e66f1ECEA06B5c30154B880200Bf57C25", # HND Gauge
        ['AAVE', 'HND'],
        "0x1205f31718499dBf1fCa446663B532Ef87481fe1", # whale
        id="USDC Generic Lender",
    ),
    pytest.param( # USDT
        "0xc2132d05d31c914a87c6611c10748aeb04b58e8f", # token
        "0x6ab707Aca953eDAeFBc4fD23bA73294241490620", # aToken
        "0x103f2CA2148B863942397dbc50a425cc4f4E9A27", # hToken
        "0x274E94f03AC51779D14bD45aF77C0e0e9d97cef9", # HND Gauge
        ['AAVE', 'HND'],
        "0x72a53cdbbcc1b9efa39c834a540550e23463aacb", # whale
        id="USDT Generic Lender",
    ),
    pytest.param( # WETH
        "0x7ceb23fd6bc0add59e62ac25578270cff1b9f619", # token
        "0xe50fA9b3c56FfB159cB0FCA61F5c9D750e8128c8", # aToken
        "0x243E33aa7f6787154a8E59d3C27a66db3F8818ee", # hToken
        "", # HND Gauge
        ['AAVE'],
        "0x72a53cdbbcc1b9efa39c834a540550e23463aacb", # whale
        id="WETH Generic Lender",
    ),
    pytest.param( # WBTC
        "0x1bfd67037b42cf73acf2047067bd4f2c47d9bfd6", # token
        "0x078f358208685046a11C85e8ad32895DED33A249", # aToken
        "0xb4300e088a3AE4e624EE5C71Bc1822F68BB5f2bc", # hToken
        "", # HND Gauge
        ['AAVE'],
        "0xdc9232e2df177d7a12fdff6ecbab114e2231198d", # whale
        id="WBTC Generic Lender",
    )
]

@pytest.fixture
def router():
    yield Contract('0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff')
    
@pytest.fixture
def weth():
    yield "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270"
    
@pytest.fixture
def hnd():
    yield "0x10010078a54396F62c96dF8532dc2B4847d47ED3"

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
        yield request.param

@pytest.fixture
def hToken(request, interface):
    if request.param == '':
        yield ''
    else:
        yield interface.CErc20I(request.param)

@pytest.fixture
def hGuage(request, interface):
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
    amount = int((1000000 / price) * (10 ** token.decimals()))
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
    weth,
    router,
    Strategy,
    GenericAave,
    fn_isolation
):
    strategy = strategist.deploy(Strategy, vault, weth, router)
    strategy.setKeeper(keeper)
    strategy.setWithdrawalThreshold(0)
    yield strategy

@pytest.fixture
def lenderAAVE(
    strategist,
    strategy,
    aToken,
    GenericAave,
    lenders
):
    if 'AAVE' in lenders:
        yield strategist.deploy(GenericAave, strategy, "AAVE", aToken, False)
    else: 
        yield ''

@pytest.fixture
def lenderHND(
    strategist,
    strategy,
    hToken,
    hGuage,
    weth, 
    router,
    hnd,
    GenericHundredFinance,
    lenders
):
    if 'HND' in lenders:
        yield strategist.deploy(GenericHundredFinance, strategy, "HundredFinance", hToken, hGuage, weth, router, hnd)
    else: 
        yield ''

# Function scoped isolation fixture to enable xdist.
# Snapshots the chain before each test and reverts after test completion.
@pytest.fixture(scope="function", autouse=True)
def shared_setup(fn_isolation, lenders, aToken, hToken, hGuage):
    pass

@pytest.fixture
def dust(decimals):
    yield int(10 ** (decimals - 8))

@pytest.fixture
def strategyAllLenders(
    strategy,
    gov,
    lenderAAVE,
    lenderHND,
    lenders,
    dust
):
    if 'AAVE' in lenders:
        # lenderAAVE.setDustThreshold(dust, {'from': gov})
        strategy.addLender(lenderAAVE, {'from': gov})
    if 'HND' in lenders:
        lenderHND.setDustThreshold(dust, {'from': gov})
        strategy.addLender(lenderHND, {'from': gov})
    assert strategy.numLenders() == len(lenders)

@pytest.fixture
def strategyAddAAVE(
    strategy,
    gov,
    lenderAAVE,
    lenders,
    dust
):
    if 'AAVE' not in lenders:
        pytest.skip()
    strategy.addLender(lenderAAVE, {'from': gov})
    # lenderAAVE.setDustThreshold(dust, {'from': gov})
    assert strategy.numLenders() == 1

@pytest.fixture
def strategyAddHND(
    strategy,
    gov,
    lenderHND,
    lenders,
    dust
):
    if 'HND' not in lenders:
        pytest.skip()
    strategy.addLender(lenderHND, {'from': gov})
    lenderHND.setDustThreshold(dust, {'from': gov})
    assert strategy.numLenders() == 1

    
