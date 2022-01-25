import pytest
from brownie import Wei, config, Contract

@pytest.fixture
def ftm_dai(interface):
    #ftm dai!
    yield interface.ERC20('0x8D11eC38a3EB5E956B052f67Da8Bdc9bef8Abf3E')

@pytest.fixture
def ftm_usdc(interface):
    #ftm usdc
    yield interface.ERC20('0x04068DA6C83AFCFA0e13ba15A6696662335D5B75')

@pytest.fixture
def scrDai(interface):
    yield interface.CErc20I("0x8D9AED9882b4953a0c9fa920168fa1FDfA0eBE75")

@pytest.fixture
def crDai(interface):
    yield interface.CErc20I("0x04c762a5dF2Fa02FE868F25359E0C259fB811CfE")

@pytest.fixture
def gov(accounts):
    yield accounts[3]

@pytest.fixture
def whale(accounts):
    yield accounts.at('0x27E611FD27b276ACbd5Ffd632E5eAEBEC9761E40', True) # Whale
    # yield accounts.at("0x96d66427C18e12Ec77B5bC195c9Bf1D6d01B204a", True)

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
def vault(gov, rewards, guardian, ftm_dai, pm):
    Vault = pm(config["dependencies"][0]).Vault
    vault = Vault.deploy({"from": guardian})
    vault.initialize(ftm_dai, gov, rewards, "", "")
    vault.setDepositLimit(2**256-1, {"from": gov})

    yield vault

@pytest.fixture
def Vault(pm):
    yield pm(config["dependencies"][0]).Vault

@pytest.fixture
def live_ftm_dai_strategy(
    Strategy
): 
    yield Strategy.at('0x754133e0f67CB51263d6d5F41f2dF1a58a9D36b7')


@pytest.fixture
def strategy(
    strategist,
    keeper,
    vault,
    scrDai,
    crDai,
    gov,
    Strategy,
    GenericScream,
    GenericIronBank
):
    strategy = strategist.deploy(Strategy, vault)
    strategy.setKeeper(keeper)

    screamPlugin = strategist.deploy(GenericScream, strategy, "Scream", scrDai)
    ibPlugin = strategist.deploy(GenericIronBank, strategy, "IB", crDai)
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
