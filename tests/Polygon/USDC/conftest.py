import pytest
from brownie import Wei, config, Contract

@pytest.fixture
def token(interface):
    yield interface.ERC20('')

@pytest.fixture
def aToken(interface):
    yield interface.CErc20I("0x1a13F4Ca1d028320A707D99520AbFefca3998b7F")

# @pytest.fixture
# def crToken(interface):
#     yield interface.CErc20I("0x328A7b4d538A2b3942653a9983fdA3C12c571141")

@pytest.fixture
def gov(accounts):
    yield accounts[3]

@pytest.fixture
def whale(accounts):
    yield accounts.at('', True)

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
    aToken,
    gov,
    Strategy,
    GenericAave
):
    strategy = strategist.deploy(Strategy, vault)
    strategy.setKeeper(keeper)

    # screamPlugin = strategist.deploy(GenericScream, strategy, "Scream", scrToken)
    # ibPlugin = strategist.deploy(GenericIronBank, strategy, "IB", crToken)
    aavePlugin = strategist.deploy(GenericAave, strategy, "IB", aToken)
    assert aavePlugin.underlyingBalanceStored() == 0
    # scapr = screamPlugin.compBlockShareInWant(0, False) * 3154 * 10**4
    # print(scapr/1e18)
    # print((screamPlugin.apr() - scapr)/1e18)

    # scapr2 = aavePlugin.compBlockShareInWant(5_000_000 * 1e6, True) * 3154 * 10**4
    # print(scapr2/1e18)
    # assert scapr2 < scapr
    strategy.addLender(aavePlugin, {"from": gov})
    # strategy.addLender(ibPlugin, {"from": gov})
    assert strategy.numLenders() == 1
    yield strategy
