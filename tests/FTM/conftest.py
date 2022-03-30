import pytest
from brownie import Wei, config, Contract, accounts

fixtures = "token", "scrToken", "ibToken", "hToken", "hGuage", "hChef", "hPID", "lenders", "whale"
params = [
    pytest.param( # USDC
        "0x04068DA6C83AFCFA0e13ba15A6696662335D5B75", # token
        "0xE45Ac34E528907d0A0239ab5Db507688070B20bf", # scrToken
        "0x328A7b4d538A2b3942653a9983fdA3C12c571141", # ib cToken
        "0x243E33aa7f6787154a8E59d3C27a66db3F8818ee", # HND hToken
        "0x110614276F7b9Ae8586a1C1D9Bc079771e2CE8cF", # HND Gauge
        "0x9A07fB107b9d8eA8B82ECF453Efb7cFb85A66Ce9", # LQDR HND Chef
        0, # hPID
        ['Scream', 'IB', 'HND', 'LqdrHND'],
        "0xe578C856933D8e1082740bf7661e379Aa2A30b26",
        id="USDC Generic Lender",
    ),
    pytest.param( # FRAX
        "0xdc301622e621166BD8E82f2cA0A26c13Ad0BE355", # token
        "0x4E6854EA84884330207fB557D1555961D85Fc17E", # scrToken
        "", # ib cToken
        "0xb4300e088a3AE4e624EE5C71Bc1822F68BB5f2bc", # HND hToken
        "0x2c7a9d9919f042C4C120199c69e126124d09BE7c", # HND Gauge
        "", # LQDR HND Chef
        0, # hPID
        ['HND', 'Scream'],
        "0x7a656B342E14F745e2B164890E88017e27AE7320",
        id="FRAX Generic Lender",
    ),
    pytest.param( # WETH
        "0x74b23882a30290451A17c44f4F05243b6b58C76d", # token
        "0xC772BA6C2c28859B7a0542FAa162a56115dDCE25", # scrToken
        "", # ib cToken
        "", # HND hToken
        "", # HND Gauge
        "", # LQDR HND Chef
        0, # hPID
        ['Scream'],
        "0x25c130B2624CF12A4Ea30143eF50c5D68cEFA22f",
        id="WETH Generic Lender",
    ),
    pytest.param( # WFTM
        "0x21be370D5312f44cB42ce377BC9b8a0cEF1A4C83", # token
        "0x5AA53f03197E08C4851CAD8C92c7922DA5857E5d", # scrToken
        "", # ib cToken
        "", # HND hToken
        "", # HND Gauge
        "", # LQDR HND Chef
        0, # hPID
        ['Scream'],
        "0x2A651563C9d3Af67aE0388a5c8F89b867038089e",
        id="WFTM Generic Lender",
    ),
]

@pytest.fixture
def router():
    yield Contract('0xF491e7B69E4244ad4002BC14e878a34207E38c29')
    
@pytest.fixture
def weth():
    yield "0x21be370D5312f44cB42ce377BC9b8a0cEF1A4C83"

# specific addresses
@pytest.fixture
def usdc(interface):
    yield interface.ERC20("0x04068DA6C83AFCFA0e13ba15A6696662335D5B75")

@pytest.fixture
def token(request, interface):
    yield interface.IERC20Extended(request.param)

@pytest.fixture
def scrToken(request, interface):
    if request.param == '':
        yield ''
    else:
        yield interface.CErc20I(request.param)

@pytest.fixture
def ibToken(request, interface):
    if request.param == '':
        yield ''
    else:
        yield interface.CErc20I(request.param)

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
def hChef(request, interface):
    yield request.param

@pytest.fixture
def hPID(request, interface):
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
    gov,
    Strategy,
    GenericScream,
    GenericIronBank,
    GenericHundredFinance,
    GenericHundredFinanceLqdr,
    fn_isolation
):
    strategy = strategist.deploy(Strategy, vault)
    strategy.setKeeper(keeper)
    strategy.setWithdrawalThreshold(0)
    yield strategy

@pytest.fixture
def lenderScream(
    strategist,
    strategy,
    scrToken,
    GenericScream,
    lenders
):
    if 'Scream' in lenders:
        yield strategist.deploy(GenericScream, strategy, "Scream", scrToken)
    else: 
        yield ''

@pytest.fixture
def lenderIB(
    strategist,
    strategy,
    ibToken,
    GenericIronBank,
    lenders
):    
    if 'IB' in lenders:
        yield strategist.deploy(GenericIronBank, strategy, "IB", ibToken)
    else: 
        yield ''
    
@pytest.fixture
def lenderHND(
    strategist,
    strategy,
    hToken,
    hGuage,
    GenericHundredFinance,
    lenders
):
    if 'HND' in lenders:
        yield strategist.deploy(GenericHundredFinance, strategy, "Hundred Finance", hToken, hGuage)
    else: 
        yield ''

@pytest.fixture
def lenderLqdrHND(
    strategist,
    strategy,
    hToken,
    hGuage,
    hChef,
    hPID,
    GenericHundredFinanceLqdr,
    lenders
):
    if 'LqdrHND' in lenders:
        yield strategist.deploy(GenericHundredFinanceLqdr, strategy, "Hundred Finance Lqdr", hToken, hGuage, hChef, hPID)
    else: 
        yield ''
    
# Function scoped isolation fixture to enable xdist.
# Snapshots the chain before each test and reverts after test completion.
@pytest.fixture(scope="function", autouse=True)
def shared_setup(fn_isolation, lenders, scrToken, ibToken, hToken, hGuage, hChef, hPID):
    pass

@pytest.fixture
def dust(decimals):
    yield int(10 ** (decimals - 8))

@pytest.fixture
def strategyAllLenders(
    strategy,
    gov,
    lenderScream,
    lenderIB,
    lenderHND,
    lenderLqdrHND,
    lenders,
    dust
):
    if 'Scream' in lenders:
        lenderScream.setDustThreshold(dust, {'from': gov})
        strategy.addLender(lenderScream, {'from': gov})
    if 'IB' in lenders:
        lenderIB.setDustThreshold(dust, {'from': gov})
        strategy.addLender(lenderIB, {'from': gov})
    if 'HND' in lenders:
        lenderHND.setDustThreshold(dust, {'from': gov})
        strategy.addLender(lenderHND, {'from': gov})
    if 'LqdrHND' in lenders:
        lenderLqdrHND.setDustThreshold(dust, {'from': gov})
        strategy.addLender(lenderLqdrHND, {'from': gov})
    assert strategy.numLenders() == len(lenders)

@pytest.fixture
def strategyAddScream(
    strategy,
    gov,
    lenderScream,
    lenders,
    dust
):
    if 'Scream' not in lenders:
        pytest.skip()
    strategy.addLender(lenderScream, {'from': gov})
    lenderScream.setDustThreshold(dust, {'from': gov})
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
    lenderIB.setDustThreshold(dust, {'from': gov})
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

@pytest.fixture
def strategyAddLqdrHND(
    strategy,
    gov,
    lenderLqdrHND,
    lenders,
    dust
):
    if 'LqdrHND' not in lenders:
        pytest.skip()
    strategy.addLender(lenderLqdrHND, {'from': gov})
    lenderLqdrHND.setDustThreshold(dust, {'from': gov})
    assert strategy.numLenders() == 1
    
