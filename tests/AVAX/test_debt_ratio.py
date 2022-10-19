from itertools import count
from brownie import Wei, reverts, Contract, interface
from useful_methods import genericStateOfVault, genericStateOfStrat
import random
import brownie
import pytest
import conftest as config

@pytest.mark.parametrize(config.fixtures, config.params, indirect=True)
def test_up_down_aave(strategyAddAave, aToken, lenders, token, chain, whale, vault, strategy, strategist, accounts, decimals, amount):
    if 'Aave' not in lenders:
        pytest.skip()
    run_up_down_test(None, token, chain, whale, vault, strategy, strategist, accounts, decimals, amount)

@pytest.mark.parametrize(config.fixtures, config.params, indirect=True)
def test_up_down_benqi(strategyAddBenqi, qiToken, lenders, token, chain, whale, vault, strategy, strategist, accounts, decimals, amount):
    if 'Benqi' not in lenders:
        pytest.skip()
    # sAavax doesn't like us to call mint(0), so we don't do that
    if(token.symbol() == 'sAVAX'):
        qiToken = None
    run_up_down_test(qiToken, token, chain, whale, vault, strategy, strategist, accounts, decimals, amount)

def run_up_down_test(
    cToken,
    token,
    chain,
    whale,
    vault,
    strategy,
    strategist,
    accounts,
    decimals,
    amount
):
    assert strategy.numLenders() == 1
    gov = accounts.at(vault.governance(), force=True)
    lender = interface.IGenericLender(strategy.lenders(0))

    strategy.setDebtThreshold(1*1e6, {"from": gov})
    strategy.setProfitFactor(1500, {"from": gov})
    strategy.setMaxReportDelay(86000, {"from": gov})

    starting_balance = token.balanceOf(whale)
    decimals = token.decimals()

    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    token.approve(vault, 2 ** 256 - 1, {"from": strategist})

    deposit_limit = 1_000_000_000 * (10 ** (decimals))
    debt_ratio = 10000

    vault.addStrategy(strategy, debt_ratio, 0, 2 ** 256 - 1, 500, {"from": gov})
    vault.setDepositLimit(deposit_limit, {"from": gov})
    assert deposit_limit == vault.depositLimit()

    whale_deposit = amount
    vault.deposit(whale_deposit, {"from": whale})

    chain.sleep(20)
    chain.mine(20)
    strategy.harvest({"from": strategist})
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=1e-5) == whale_deposit

    status = strategy.lendStatuses()
    form = "{:.2%}"
    formS = "{:,.0f}"
    for j in status:
        print(
            f"Lender: {j[0]}, Deposits: {formS.format(j[1]/(10 ** decimals))}, APR: {form.format(j[2]/1e18)}"
        )
    chain.sleep(20)
    chain.mine(20)

    if (cToken is not None):
          cToken.mint(0, {"from": strategist})

    # Set debt ratio to zero to clear out the strategy
    vault.updateStrategyDebtRatio(strategy, 0, {"from": gov})
    print(strategy.lendStatuses())
    strategy.harvest({"from": strategist})
    assert strategy.estimatedTotalAssets() / vault.totalAssets() < 1e-5
    print(lender.hasAssets())
    chain.mine(20)
    if (cToken is not None):
        cToken.mint(0, {"from": strategist})
    chain.mine(20)
    chain.sleep(20)
    strategy.harvest({"from": strategist})

    print(lender.hasAssets())
    chain.mine(20)
    if (cToken is not None):
        cToken.mint(0, {"from": strategist})

    chain.mine(20)
    chain.sleep(20)
    strategy.harvest({"from": strategist})
    print(lender.hasAssets())
    status = strategy.lendStatuses()
    for j in status:
        print(
            f"Lender: {j[0]}, Deposits: {formS.format(j[1]/(10 ** decimals))}, APR: {form.format(j[2]/1e18)}"
        )
    chain.mine(20)
    if (cToken is not None):
        cToken.mint(0, {"from": strategist})
    chain.sleep(20)

    vault.updateStrategyDebtRatio(strategy, 10_000, {"from": gov})
    strategy.harvest({"from": strategist})
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=1e-5) == whale_deposit

    status = strategy.lendStatuses()
    for j in status:
        print(
            f"Lender: {j[0]}, Deposits: {formS.format(j[1]/(10 ** decimals))}, APR: {form.format(j[2]/1e18)}"
        )