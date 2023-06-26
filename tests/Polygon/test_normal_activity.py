from itertools import count
from brownie import Wei, reverts, Contract, interface, GenericAaveV3
from useful_methods import genericStateOfVault, genericStateOfStrat
import random
import brownie
import pytest
import conftest as config

#@pytest.mark.skip
@pytest.mark.parametrize(config.fixtures, config.params, indirect=True)
def test_normal_activity_all(strategyAllLenders, token, aToken, qiToken, iToken, chain, whale, vault, strategy, gov, strategist, lenders, amount, decimals):
    run_normal_activity_test(token, aToken, qiToken, iToken, chain, whale, vault, strategy, gov, strategist, lenders, amount, decimals, len(lenders))

#@pytest.mark.skip
@pytest.mark.parametrize(config.fixtures, config.params, indirect=True)
def test_normal_activity_aave(strategyAddAave, token, aToken, qiToken, iToken, chain, whale, vault, strategy, gov, strategist, lenders, amount, decimals):
    run_normal_activity_test(token, aToken, qiToken, iToken, chain, whale, vault, strategy, gov, strategist, lenders, amount, decimals, 1)

#@pytest.mark.skip
@pytest.mark.parametrize(config.fixtures, config.params, indirect=True)
def test_normal_activity_benqi(strategyAddBenqi, token, aToken, qiToken, iToken, chain, whale, vault, strategy, gov, strategist, lenders, amount, decimals):
    run_normal_activity_test(token, aToken, qiToken, iToken, chain, whale, vault, strategy, gov, strategist, lenders, amount, decimals, 1)

@pytest.mark.parametrize(config.fixtures, config.params, indirect=True)
def test_normal_activity_ib(strategyAddIB, token, aToken, qiToken, iToken, chain, whale, vault, strategy, gov, strategist, lenders, amount, decimals):
    run_normal_activity_test(token, aToken, qiToken, iToken, chain, whale, vault, strategy, gov, strategist, lenders, amount, decimals, 1)

def run_normal_activity_test(
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
    decimals,
    lendersSize
):
    starting_balance = token.balanceOf(strategist)
    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    token.approve(vault, 2 ** 256 - 1, {"from": strategist})

    debt_ratio = 10_000
    vault.addStrategy(strategy, debt_ratio, 0, 2 ** 256 - 1, 1000, {"from": gov})

    whale_deposit = amount
    vault.deposit(whale_deposit, {"from": whale})
    chain.sleep(1)
    chain.mine(1)
    strategy.setWithdrawalThreshold(0, {"from": gov})
    #assert strategy.harvestTrigger(1) == True
    print(whale_deposit / 1e18)
    status = strategy.lendStatuses()
    form = "{:.2%}"
    formS = "{:,.0f}"
    for j in status:
        print(
            f"Lender: {j[0]}, Deposits: {formS.format(j[1]/(10 ** decimals))} APR: {form.format(j[2]/1e18)}"
        )

    strategy.harvest({"from": strategist})

    status = strategy.lendStatuses()
    form = "{:.2%}"
    formS = "{:,.0f}"
    for j in status:
        print(
            f"Lender: {j[0]}, Deposits: {formS.format(j[1]/(10 ** decimals))} APR: {form.format(j[2]/1e18)}"
        )
    startingBalance = vault.totalAssets()
    for i in range(4):
        waitBlock = 25
        print(f'\n----wait {waitBlock} blocks----')
        chain.mine(waitBlock)
        chain.sleep(waitBlock)
        print(f'\n----harvest----')
        if 'Benqi' in lenders:
            token.approve(qiToken, 1, {"from": whale})
            qiToken.mint(1,{"from": whale})
        if 'Aave' in lenders:
            for j in range(lendersSize):
                lender = interface.IGenericLender(strategy.lenders(j))
                if lender.lenderName() == 'Aave':
                    GenericAaveV3.at(lender.address).harvest({"from": gov})

        if 'IB' in lenders:
            token.approve(iToken, 1, {"from": whale})
            iToken.mint(1,{"from": whale})
        strategy.harvest({"from": strategist})
        
        # genericStateOfStrat(strategy, currency, vault)
        # genericStateOfVault(vault, currency)

        profit = (vault.totalAssets() - startingBalance) / 1e6
        strState = vault.strategies(strategy)
        totalReturns = strState[7]
        totaleth = totalReturns / 1e6
        # print(f'Real Profit: {profit:.5f}')
        difff = profit - totaleth
        # print(f'Diff: {difff}')

        blocks_per_year = 3156 * 10**4  
        assert startingBalance != 0
        time = (i + 1) * waitBlock
        assert time != 0
        apr = (totalReturns / startingBalance) * (blocks_per_year / time)
        assert apr > 0 and apr < 10
        # print(apr)
        print(f"implied apr: {apr:.8%}")

    vault.withdraw(vault.balanceOf(whale), {"from": whale})

    vBal = vault.balanceOf(strategy)
    assert vBal > 0
    print(vBal)
    vBefore = vault.balanceOf(strategist)
    vault.transferFrom(strategy, strategist, vBal, {"from": strategist})
    print(vault.balanceOf(strategist) - vBefore)
    assert vault.balanceOf(strategist) - vBefore > 0
