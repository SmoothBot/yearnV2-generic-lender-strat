import pytest
from brownie import Wei, config, Contract

fixtures = "token", "scrToken", "ibToken", "hToken", "hGuage", "hChef", "hPID", "lenders"
params = [
    pytest.param( # WFTM
        "0x04068DA6C83AFCFA0e13ba15A6696662335D5B75", # token
        "0xE45Ac34E528907d0A0239ab5Db507688070B20bf", # scrToken
        "0x328A7b4d538A2b3942653a9983fdA3C12c571141", # ib cToken
        "0x243E33aa7f6787154a8E59d3C27a66db3F8818ee", # HND hToken
        "0x110614276F7b9Ae8586a1C1D9Bc079771e2CE8cF", # HND Gauge
        "0x9A07fB107b9d8eA8B82ECF453Efb7cFb85A66Ce9", # LQDR HND Chef
        0, # hPID
        ['Scream', 'IB', 'HND', 'LqdrHND'],
        id="USDC Generic Lender",
    ),
]

@pytest.fixture
def router():
    yield Contract('0xF491e7B69E4244ad4002BC14e878a34207E38c29')
    
@pytest.fixture
def weth():
    token_address = "0x21be370D5312f44cB42ce377BC9b8a0cEF1A4C83"

# specific addresses
@pytest.fixture
def usdc(interface):
    yield interface.ERC20("0x04068DA6C83AFCFA0e13ba15A6696662335D5B75")

@pytest.fixture
def token(request, interface):
    yield interface.IERC20Extended(request.param)

@pytest.fixture
def scrToken(request, interface):
    yield interface.CErc20I(request.param)

@pytest.fixture
def ibToken(request, interface):
    yield interface.CErc20I(request.param)

@pytest.fixture
def hToken(request, interface):
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
def gov(accounts):
    yield accounts[3]

@pytest.fixture
def whale(accounts):
    yield accounts.at('0xe578C856933D8e1082740bf7661e379Aa2A30b26', True)

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
    scrToken,
    ibToken,
    hToken,
    hGuage,
    hChef,
    hPID,
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
    ibToken,
    GenericScream,
    lenders
):
    yield strategist.deploy(GenericScream, strategy, "Scream", scrToken)

@pytest.fixture
def lenderIB(
    strategist,
    strategy,
    ibToken,
    GenericIronBank,
):    
    yield strategist.deploy(GenericIronBank, strategy, "IB", ibToken)

@pytest.fixture
def lenderHND(
    strategist,
    strategy,
    hToken,
    hGuage,
    GenericHundredFinance
):
    yield strategist.deploy(GenericHundredFinance, strategy, "Hundred Finance", hToken, hGuage)

@pytest.fixture
def lenderLqdrHND(
    strategist,
    strategy,
    hToken,
    hGuage,
    hChef,
    hPID,
    GenericHundredFinanceLqdr
):
    yield strategist.deploy(GenericHundredFinanceLqdr, strategy, "Hundred Finance Lqdr", hToken, hGuage, hChef, hPID)

# Function scoped isolation fixture to enable xdist.
# Snapshots the chain before each test and reverts after test completion.
@pytest.fixture(scope="function", autouse=True)
def shared_setup(fn_isolation, lenders):
    pass

@pytest.fixture
def strategyAllLenders(
    strategy,
    gov,
    lenderScream,
    lenderIB,
    lenderHND,
    lenderLqdrHND,
    lenders
):
    lenderScream.setDustThreshold(0, {'from': gov})
    lenderIB.setDustThreshold(0, {'from': gov})
    lenderHND.setDustThreshold(0, {'from': gov})
    lenderLqdrHND.setDustThreshold(0, {'from': gov})
    if 'Scream' in lenders:
        strategy.addLender(lenderScream, {'from': gov})
    if 'IB' in lenders:
        strategy.addLender(lenderIB, {'from': gov})
    if 'HND' in lenders:
        strategy.addLender(lenderHND, {'from': gov})
    if 'LqdrHND' in lenders:
        strategy.addLender(lenderLqdrHND, {'from': gov})
    assert strategy.numLenders() == len(lenders)

@pytest.fixture
def strategyAddScream(
    strategy,
    gov,
    lenderScream
):
    strategy.addLender(lenderScream, {'from': gov})
    lenderScream.setDustThreshold(0, {'from': gov})
    assert strategy.numLenders() == 1

@pytest.fixture
def strategyAddIB(
    strategy,
    gov,
    lenderIB
):
    strategy.addLender(lenderIB, {'from': gov})
    lenderIB.setDustThreshold(0, {'from': gov})
    assert strategy.numLenders() == 1

@pytest.fixture
def strategyAddHND(
    strategy,
    gov,
    lenderHND
):
    strategy.addLender(lenderHND, {'from': gov})
    lenderHND.setDustThreshold(0, {'from': gov})
    assert strategy.numLenders() == 1

@pytest.fixture
def strategyAddLqdrHND(
    strategy,
    gov,
    lenderLqdrHND
):
    strategy.addLender(lenderLqdrHND, {'from': gov})
    lenderLqdrHND.setDustThreshold(0, {'from': gov})
    assert strategy.numLenders() == 1
    
