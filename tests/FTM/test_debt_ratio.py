from itertools import count
from brownie import Wei, reverts, Contract, interface
from useful_methods import genericStateOfVault, genericStateOfStrat
import random
import brownie
import pytest
import conftest as config


@pytest.mark.parametrize(config.fixtures, config.params, indirect=True)
def test_up_down_scream(strategyAddScream, scrToken, lenders, token, chain, whale, vault, strategy, strategist, accounts):
    if 'Scream' not in lenders:
        pass
    run_up_down_test(scrToken, token, chain, whale, vault, strategy, strategist, accounts)

@pytest.mark.parametrize(config.fixtures, config.params, indirect=True)
def test_up_down_ib(strategyAddIB, ibToken, lenders, token, chain, whale, vault, strategy, strategist, accounts):
    if 'IB' not in lenders:
        pass
    run_up_down_test(ibToken, token, chain, whale, vault, strategy, strategist, accounts)

@pytest.mark.parametrize(config.fixtures, config.params, indirect=True)
def test_up_down_hnd(strategyAddHND, hToken, lenders, token, chain, whale, vault, strategy, strategist, accounts):
    if 'HND' not in lenders:
        pass
    run_up_down_test(hToken, token, chain, whale, vault, strategy, strategist, accounts)

@pytest.mark.parametrize(config.fixtures, config.params, indirect=True)
def test_up_down_lqdr_hnd(strategyAddLqdrHND, hToken, lenders, token, chain, whale, vault, strategy, strategist, accounts):
    if 'LqdrHND' not in lenders:
        pass
    run_up_down_test(hToken, token, chain, whale, vault, strategy, strategist, accounts)

def run_up_down_test(
    cToken,
    token,
    chain,
    whale,
    vault,
    strategy,
    strategist,
    accounts
):
    assert strategy.numLenders() == 1
    token = token
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
 
    whale_deposit = 1000000 * (10 ** (decimals))
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
            f"Lender: {j[0]}, Deposits: {formS.format(j[1]/1e6)}, APR: {form.format(j[2]/1e18)}"
        )
    chain.sleep(20)
    chain.mine(20)
    cToken.mint(0, {"from": strategist})

    # Set debt ratio to zero to clear out the strategy
    vault.updateStrategyDebtRatio(strategy, 0, {"from": gov})
    strategy.harvest({"from": strategist})
    assert strategy.estimatedTotalAssets()/vault.totalAssets() < 1e-5
    print(lender.hasAssets())
    chain.mine(20)
    cToken.mint(0, {"from": strategist})
    chain.mine(20)
    chain.sleep(20)
    strategy.harvest({"from": strategist})
    
    print(lender.hasAssets())
    chain.mine(20)
    cToken.mint(0, {"from": strategist})

    chain.mine(20)
    chain.sleep(20)
    strategy.harvest({"from": strategist})
    print(lender.hasAssets())
    status = strategy.lendStatuses()
    for j in status:
        print(
            f"Lender: {j[0]}, Deposits: {formS.format(j[1]/1e6)}, APR: {form.format(j[2]/1e18)}"
        )
    chain.mine(20)
    cToken.mint(0, {"from": strategist})
    chain.sleep(20)

    vault.updateStrategyDebtRatio(strategy, 10_000, {"from": gov})
    strategy.harvest({"from": strategist})
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=1e-5) == whale_deposit

    status = strategy.lendStatuses()
    for j in status:
        print(
            f"Lender: {j[0]}, Deposits: {formS.format(j[1]/1e6)}, APR: {form.format(j[2]/1e18)}"
        )