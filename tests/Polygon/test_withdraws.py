from itertools import count
from brownie import Wei, reverts, Contract, interface
from useful_methods import genericStateOfVault, genericStateOfStrat
import random
import brownie
import pytest
import conftest as config

@pytest.mark.parametrize(config.fixtures, config.params, indirect=True)
def test_withdraw_all_aave(strategyAddAave, token, aToken, qiToken, iToken, chain, whale, vault, strategy, gov, strategist, lenders, amount, rando):
    run_withdraw_all_test(token, aToken, qiToken, iToken, chain, whale, vault, strategy, gov, strategist, lenders, amount, rando)

@pytest.mark.parametrize(config.fixtures, config.params, indirect=True)
def test_withdraw_all_benqi(strategyAddBenqi, token, aToken, qiToken, iToken, chain, whale, vault, strategy, gov, strategist, lenders, amount, rando):
    run_withdraw_all_test(token, aToken, qiToken, iToken, chain, whale, vault, strategy, gov, strategist, lenders, amount, rando)

@pytest.mark.parametrize(config.fixtures, config.params, indirect=True)
def test_withdraw_all_benqi(strategyAddIB, token, aToken, qiToken, iToken, chain, whale, vault, strategy, gov, strategist, lenders, amount, rando):
    run_withdraw_all_test(token, aToken, qiToken, iToken, chain, whale, vault, strategy, gov, strategist, lenders, amount, rando)


def run_withdraw_all_test(
    token,
    aToken,
    qiToken,
    iToken,
    chain,
    whale,
    vault,
    strategy,
    gov,
    strategist,
    lenders,
    amount,
    rando
):
    # deploy capital to the strategy
    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    vault.addStrategy(strategy, 10000, 0, 2 ** 256 - 1, 500, {"from": gov})
    vault.deposit(amount, {"from": whale})

    # Call this once to seed the strategy with debt
    chain.sleep(1)
    strategy.harvest({"from": strategist})

    # check the lender has the capital
    lender = interface.IGenericLender(strategy.lenders(0))

    assert pytest.approx(lender.nav(), rel=1e-5) == amount
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=1e-5) == amount
    chain.sleep(1)

    with brownie.reverts():
        lender.withdrawAll({'from':rando})
    lender.withdrawAll({'from':gov})

    # check all funds were liquidated in the lender and sent to the strat
    assert lender.nav() / 10 ** token.decimals() < 5 * 1e-4
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=1e-5) == amount

    # check it can harvest
    tx = strategy.harvest({"from": strategist})
    assert tx.events['StrategyReported']['loss'] == 0

    vault.withdraw({'from':whale})

