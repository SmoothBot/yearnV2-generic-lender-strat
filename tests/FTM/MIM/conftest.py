import pytest
from brownie import Wei, config, Contract

@pytest.fixture
def token(interface):
    yield interface.ERC20('0x82f0B8B456c1A451378467398982d4834b6829c1')

@pytest.fixture
def scrToken(interface):
    yield interface.CErc20I("0x90B7C21Be43855aFD2515675fc307c084427404f")

@pytest.fixture
def crToken(interface):
    yield interface.CErc20I("0x46F298D5bB6389ccb6C1366bB0C8a30892CA2f7C")

@pytest.fixture
def gov(accounts):
    yield accounts[3]

@pytest.fixture
def whale(accounts):
    yield accounts.at('0xc664Fc7b8487a3E10824Cda768c1d239F2403bBe', True)

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
    gov,
    Strategy,
    GenericScream,
    GenericIronBank
):
    strategy = strategist.deploy(Strategy, vault)
    strategy.setKeeper(keeper)

    screamPlugin = strategist.deploy(GenericScream, strategy, "Scream", scrToken)
    ibPlugin = strategist.deploy(GenericIronBank, strategy, "IB", crToken)
    assert screamPlugin.underlyingBalanceStored() == 0
    scapr = screamPlugin.compBlockShareInWant(0, False) * 3154 * 10**4
    print(scapr/1e18)
    print((screamPlugin.apr() - scapr)/1e18)

    scapr2 = screamPlugin.compBlockShareInWant(5_000_000 * 1e18, True) * 3154 * 10**4
    print(scapr2/1e18)
    assert scapr2 < scapr
    strategy.addLender(screamPlugin, {"from": gov})
    strategy.addLender(ibPlugin, {"from": gov})
    assert strategy.numLenders() == 2
    yield strategy