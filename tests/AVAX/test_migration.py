import brownie
import pytest
from brownie import ZERO_ADDRESS, interface
import conftest as config


@pytest.mark.parametrize(config.fixtures, config.params, indirect=True)
def test_good_migration_all(
    token, strategy, strategyAllLenders, vault, gov, strategist, guardian, whale, amount, TestStrategy, rando, chain
):
    run_good_migration_test(token, strategy, vault, gov, strategist, guardian, whale, amount, TestStrategy, rando, chain)

@pytest.mark.parametrize(config.fixtures, config.params, indirect=True)
def test_good_migration_aave(
    token, strategy, strategyAddAave, vault, gov, strategist, guardian, whale, amount, TestStrategy, rando, chain
):
    run_good_migration_test(token, strategy, vault, gov, strategist, guardian, whale, amount, TestStrategy, rando, chain)

@pytest.mark.parametrize(config.fixtures, config.params, indirect=True)
def test_good_migration_benqi(
    token, strategy, strategyAddBenqi, vault, gov, strategist, guardian, whale, amount, TestStrategy, rando, chain
):
    run_good_migration_test(token, strategy, vault, gov, strategist, guardian, whale, amount, TestStrategy, rando, chain)

def run_good_migration_test(
    token, strategy, vault, gov, strategist, guardian, whale, amount, TestStrategy, rando, chain
):
    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    vault.addStrategy(strategy, 10000, 0, 2 ** 256 - 1, 500, {"from": gov})
    vault.deposit(amount, {"from": whale})

    # Call this once to seed the strategy with debt
    chain.sleep(1)
    strategy.harvest({"from": strategist})

    strategy_debt = vault.strategies(strategy).dict()["totalDebt"]
    assert pytest.approx(strategy.estimatedTotalAssets(), 1e-5) == strategy_debt

    new_strategy = strategist.deploy(TestStrategy, vault)
    assert vault.strategies(new_strategy).dict()["totalDebt"] == 0
    assert token.balanceOf(new_strategy) == 0

    # Only Governance can migrate
    with brownie.reverts():
        vault.migrateStrategy(strategy, new_strategy, {"from": rando})
    with brownie.reverts():
        vault.migrateStrategy(strategy, new_strategy, {"from": strategist})
    with brownie.reverts():
        vault.migrateStrategy(strategy, new_strategy, {"from": guardian})

    vault.migrateStrategy(strategy, new_strategy, {"from": gov})
    assert vault.strategies(strategy).dict()["totalDebt"] == 0
    assert strategy.estimatedTotalAssets() / amount < 1e-5
    assert (
        pytest.approx(vault.strategies(new_strategy).dict()["totalDebt"], 1e-5)
        == pytest.approx(token.balanceOf(new_strategy), 1e-5)
        == strategy_debt
    )

    with brownie.reverts():
        new_strategy.migrate(strategy, {"from": gov})


@pytest.mark.parametrize(config.fixtures, config.params, indirect=True)
def test_bad_migration(
    token, vault, strategy, strategyAllLenders, gov, strategist, TestStrategy, Vault, whale, amount, rando, chain
):
    # add strat and deploy capital to vault
    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    vault.addStrategy(strategy, 10000, 0, 2 ** 256 - 1, 500, {"from": gov})
    vault.deposit(amount, {"from": whale})
    chain.sleep(1)
    strategy.harvest({"from": strategist})

    different_vault = gov.deploy(Vault)
    different_vault.initialize(
        token, gov, gov, token.symbol() + " yVault", "yv" + token.symbol(), gov
    )
    different_vault.setDepositLimit(2 ** 256 - 1, {"from": gov})
    new_strategy = strategist.deploy(TestStrategy, different_vault)

    # Can't migrate to a strategy with a different vault
    with brownie.reverts():
        vault.migrateStrategy(strategy, new_strategy, {"from": gov})

    new_strategy = strategist.deploy(TestStrategy, vault)

    # Can't migrate if you're not the Vault  or governance
    with brownie.reverts():
        strategy.migrate(new_strategy, {"from": rando})

    # Can't migrate if new strategy is 0x0 - Brownie is bugged, thinks this isn't reverting. 
    with brownie.reverts():
        vault.migrateStrategy(strategy, ZERO_ADDRESS, {"from": gov})


@pytest.mark.parametrize(config.fixtures, config.params, indirect=True)
def test_migrated_strategy_can_call_harvest(
    token, strategy, strategyAllLenders, vault, gov, strategist, guardian, whale, amount, TestStrategy, rando, chain, lenders, aToken, qiToken
):
    # add strat and deploy capital to vault
    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    vault.addStrategy(strategy, 10000, 0, 2 ** 256 - 1, 500, {"from": gov})
    vault.deposit(amount, {"from": whale})
    chain.mine(10)
    chain.sleep(10)
    strategy.harvest({"from": strategist})

    # Deploy new strategy and migrate
    new_strategy = gov.deploy(TestStrategy, vault)
    vault.migrateStrategy(strategy, new_strategy, {"from": gov})

    # send profit to the old strategy
    token.transfer(strategy, 10 ** token.decimals(), {"from": whale})

    assert vault.strategies(strategy).dict()["totalGain"] == 0
    chain.mine(10)
    chain.sleep(10)

    for i in range(strategy.numLenders()):
        interface.IGenericLenderExt(strategy.lenders(i)).setDustThreshold(0, {'from':strategist})
    
    strategy.harvest({"from": gov})
    assert vault.strategies(strategy).dict()["totalGain"] >= 10 ** token.decimals()

    # But after migrated it cannot be added back
    vault.updateStrategyDebtRatio(new_strategy, 5_000, {"from": gov})
    with brownie.reverts():
        vault.addStrategy(strategy, 5_000, 0, 1000, 0, {"from": gov})
