import pytest
from brownie import Wei, config, Contract

@pytest.fixture
def token(interface):
    yield interface.ERC20('0x04068DA6C83AFCFA0e13ba15A6696662335D5B75')

@pytest.fixture
def scrToken(interface):
    yield interface.CErc20I("0xE45Ac34E528907d0A0239ab5Db507688070B20bf")

@pytest.fixture
def hundredGauge(interface):
    yield "0x110614276F7b9Ae8586a1C1D9Bc079771e2CE8cF"
    
@pytest.fixture
def crToken(interface):
    yield interface.CErc20I("0x328A7b4d538A2b3942653a9983fdA3C12c571141")

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

@pytest.fixture
def keeper(accounts):
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

@pytest.fixture
def live_strategy(
    Strategy
): 
    yield Strategy.at('0x754133e0f67CB51263d6d5F41f2dF1a58a9D36b7')


@pytest.fixture
def strategy(
    strategist,
    keeper,
    vault,
    scrToken,
    crToken,
    hundredGauge,
    gov,
    Strategy,
    GenericScream,
    GenericIronBank,
    GenericHundredFinance
):
    strategy = strategist.deploy(Strategy, vault)
    strategy.setKeeper(keeper)

    screamPlugin = strategist.deploy(GenericScream, strategy, "Scream", scrToken)
    ibPlugin = strategist.deploy(GenericIronBank, strategy, "IB", crToken)
    hndPlugin = strategist.deploy(GenericHundredFinance, strategy, "Hundred Finance", crToken, hundredGauge)
    assert screamPlugin.underlyingBalanceStored() == 0
    scapr = screamPlugin.compBlockShareInWant(0, False) * 3154 * 10**4
    print(scapr/1e18)
    print((screamPlugin.apr() - scapr)/1e18)

    scapr2 = screamPlugin.compBlockShareInWant(5_000_000 * 1e6, True) * 3154 * 10**4
    print(scapr2/1e18)
    assert scapr2 < scapr
    strategy.addLender(screamPlugin, {"from": gov})
    strategy.addLender(ibPlugin, {"from": gov})
    strategy.addLender(hndPlugin, {"from": gov})
    assert strategy.numLenders() == 3
    yield strategy
