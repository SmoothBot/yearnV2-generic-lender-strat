from itertools import count
from brownie import Wei, reverts, Contract, interface
from useful_methods import genericStateOfVault, genericStateOfStrat
import random
import brownie
import pytest
import conftest as config

@pytest.mark.parametrize(config.fixtures, config.params, indirect=True)
def test_emergency_exit_aave(strategyAddAURI, lenders, token, chain, whale, vault, strategy, gov, strategist, amount):
    if 'AURI' not in lenders:
        pytest.skip()
    run_emergency_exit_test(token, chain, whale, vault, strategy, gov, strategist, amount)


def run_emergency_exit_test(
    token,
    chain,
    whale,
    vault,
    strategy,
    gov,
    strategist,
    amount
):
    starting_balance = token.balanceOf(strategist)

    token.approve(vault, 2 ** 256 - 1, {"from": whale})

    debt_ratio = 10_000
    vault.addStrategy(strategy, debt_ratio, 0, 2 ** 256 - 1, 1000, {"from": gov})

    vault.deposit(amount, {"from": whale})
    chain.sleep(1)
    chain.mine(1)
    strategy.setWithdrawalThreshold(0, {"from": gov})
    assert strategy.harvestTrigger(1 * 1e14) == True

    # load up the strategy and lender with capital
    strategy.harvest({"from": strategist})
    lender = interface.IGenericLender(strategy.lenders(0))
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=1e-5) == amount
    assert pytest.approx(lender.nav(), rel=1e-5) == amount
    chain.sleep(1)
    chain.mine(1)

    # load up the strategy and lender with capital
    strategy.harvest({"from": strategist})
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=1e-5) == amount

    # Emergency withdraw sends all assets to governance in case of an emergency.
    govBalanceBefore = token.balanceOf(gov)
    lender.emergencyWithdraw(lender.nav(), {"from": gov})

    # check there's nothing left in the strat and it's all in the gov
    dust = amount * (0.005)
    assert strategy.estimatedTotalAssets() < dust
    assert pytest.approx(token.balanceOf(gov), rel=1e-5) == govBalanceBefore + amount
