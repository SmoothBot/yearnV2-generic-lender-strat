import pytest
from brownie import Wei, config, Contract

fixtures = "token", "scrToken", "ibToken", "hToken", "hGuage", "hChef", "hPID"
params = [
    pytest.param( # WFTM
        "0x04068DA6C83AFCFA0e13ba15A6696662335D5B75", # token
        "0xE45Ac34E528907d0A0239ab5Db507688070B20bf", # scrToken
        "0x328A7b4d538A2b3942653a9983fdA3C12c571141", # ib cToken
        "0x243E33aa7f6787154a8E59d3C27a66db3F8818ee", # HND hToken
        "0x110614276F7b9Ae8586a1C1D9Bc079771e2CE8cF", # HND Gauge
        "0x9A07fB107b9d8eA8B82ECF453Efb7cFb85A66Ce9", # LQDR HND Chef
        0, # hPID
        id="USDC Generic Lender",
    ),
]


@pytest.fixture
def token(request, interface):
    yield interface.ERC20(request.param)

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
    # This is our trusty bot!
    yield accounts[4]

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

# @pytest.fixture
# def live_strategy(
#     Strategy
# ): 
#     yield Strategy.at('0x754133e0f67CB51263d6d5F41f2dF1a58a9D36b7')

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
    GenericHundredFinanceLqdr
    
):
    strategy = strategist.deploy(Strategy, vault)
    strategy.setKeeper(keeper)
    
    # screamPlugin = strategist.deploy(GenericScream, strategy, "Scream", scrToken)
    # ibPlugin = strategist.deploy(GenericIronBank, strategy, "IB", ibToken)
    # hndPlugin = strategist.deploy(GenericHundredFinance, strategy, "Hundred Finance", hToken, hGuage)
    hndLQDRPlugin = strategist.deploy(GenericHundredFinanceLqdr, strategy, "Hundred Finance Lqdr", hToken, hGuage, hChef, hPID)

    # strategy.addLender(screamPlugin, {"from": gov})
    # strategy.addLender(ibPlugin, {"from": gov})
    # strategy.addLender(hndPlugin, {"from": gov})
    strategy.addLender(hndLQDRPlugin, {"from": gov})

    assert strategy.numLenders() == 1
    yield strategy


@pytest.fixture
def strategyHndLqdr(
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
    GenericHundredFinanceLqdr
    
):
    strategy = strategist.deploy(Strategy, vault)
    strategy.setKeeper(keeper)
    
    screamPlugin = strategist.deploy(GenericScream, strategy, "Scream", scrToken)
    ibPlugin = strategist.deploy(GenericIronBank, strategy, "IB", ibToken)
    hndPlugin = strategist.deploy(GenericHundredFinance, strategy, "Hundred Finance", hToken, hGuage)
    hndLQDRPlugin = strategist.deploy(GenericHundredFinanceLqdr, strategy, "Hundred Finance Lqdr", hToken, hGuage, hChef, hPID)
    assert screamPlugin.underlyingBalanceStored() == 0
    scapr = screamPlugin.compBlockShareInWant(0, False) * 3154 * 10**4
    print(scapr/1e18)
    print((screamPlugin.apr() - scapr)/1e18)

    scapr2 = screamPlugin.compBlockShareInWant(5_000_000 * 1e6, True) * 3154 * 10**4
    print(scapr2/1e18)
    assert scapr2 < scapr
    #strategy.addLender(screamPlugin, {"from": gov})
    #strategy.addLender(ibPlugin, {"from": gov})
    #strategy.addLender(hndPlugin, {"from": gov})
    strategy.addLender(hndLQDRPlugin, {"from": gov})

    assert strategy.numLenders() == 1
    yield strategy


@pytest.fixture
def strategyHnd(
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
    GenericHundredFinanceLqdr
    
):
    strategy = strategist.deploy(Strategy, vault)
    strategy.setKeeper(keeper)
    
    screamPlugin = strategist.deploy(GenericScream, strategy, "Scream", scrToken)
    ibPlugin = strategist.deploy(GenericIronBank, strategy, "IB", ibToken)
    hndPlugin = strategist.deploy(GenericHundredFinance, strategy, "Hundred Finance", hToken, hGuage)
    hndLQDRPlugin = strategist.deploy(GenericHundredFinanceLqdr, strategy, "Hundred Finance Lqdr", hToken, hGuage, hChef, hPID)
    assert screamPlugin.underlyingBalanceStored() == 0
    scapr = screamPlugin.compBlockShareInWant(0, False) * 3154 * 10**4
    print(scapr/1e18)
    print((screamPlugin.apr() - scapr)/1e18)

    scapr2 = screamPlugin.compBlockShareInWant(5_000_000 * 1e6, True) * 3154 * 10**4
    print(scapr2/1e18)
    assert scapr2 < scapr
    #strategy.addLender(screamPlugin, {"from": gov})
    #strategy.addLender(ibPlugin, {"from": gov})
    strategy.addLender(hndPlugin, {"from": gov})
    #strategy.addLender(hndLQDRPlugin, {"from": gov})

    assert strategy.numLenders() == 1
    yield strategy

# Function scoped isolation fixture to enable xdist.
# Snapshots the chain before each test and reverts after test completion.
@pytest.fixture(scope="function", autouse=True)
def shared_setup(fn_isolation):
    pass