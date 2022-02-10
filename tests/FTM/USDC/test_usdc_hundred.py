from itertools import count
from brownie import Wei, reverts
from useful_methods import genericStateOfVault, genericStateOfStrat
import random
import brownie

def test_normal_activity(
    whale,
    rando,
    vault,
    strategy,
    Contract,
    accounts,
    ibUsdc,
    hUsdc,
    ftm_usdc,
    fn_isolation,
    chain
):
    print_lenders(strategy)
    strategist = accounts.at(strategy.strategist(), force=True)
    gov = accounts.at(vault.governance(), force=True)
    currency = ftm_usdc
    starting_balance = currency.balanceOf(strategist)

    currency.approve(vault, 2 ** 256 - 1, {"from": whale})
    currency.approve(vault, 2 ** 256 - 1, {"from": strategist})

    deposit_limit = 10_000
    vault.addStrategy(strategy, deposit_limit, 0, 2 ** 256 - 1, 1000, {"from": gov})

    whale_deposit = 1_000_000 * 1e6
    vault.deposit(whale_deposit, {"from": whale})
    chain.sleep(10)
    chain.mine(1)
    strategy.setWithdrawalThreshold(0, {"from": gov})
    #assert strategy.harvestTrigger(1 * 1e18) == True
    print_lenders(strategy)


    strategy.harvest({"from": strategist})

    print_lenders(strategy)
    startingBalance = vault.totalAssets()
    for i in range(4):

        waitBlock = 25
        # print(f'\n----wait {waitBlock} blocks----')
        chain.mine(waitBlock)
        chain.sleep(waitBlock)
        # print(f'\n----harvest----')
        hUsdc.mint(0,{"from": whale})
        ibUsdc.mint(0,{"from": whale})
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

        blocks_per_year = 365*60*60*24
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


def test_scream_up_down(
    Strategy,
    scrDai,
    GenericScream,
    chain,
    whale,
    ftm_dai,
    strategist,
    vault,
    Contract,
    accounts
):
    currency = ftm_dai
    gov = accounts.at(vault.governance(), force=True)
    strategy = strategist.deploy(Strategy, vault)
    screamPlugin = strategist.deploy(GenericScream, strategy, "Scream", scrDai)
    
    strategy.setRewards(strategist, {"from": strategist})
    strategy.setWithdrawalThreshold(0, {"from": strategist})

    strategy.addLender(screamPlugin, {"from": gov})

    strategy.setDebtThreshold(1*1e6, {"from": gov})
    strategy.setProfitFactor(1500, {"from": gov})
    strategy.setMaxReportDelay(86000, {"from": gov})

    starting_balance = currency.balanceOf(whale)

    decimals = currency.decimals()
    #print(vault.withdrawalQueue(1))

    #strat2 = Contract(vault.withdrawalQueue(1))

    currency.approve(vault, 2 ** 256 - 1, {"from": whale})
    currency.approve(vault, 2 ** 256 - 1, {"from": strategist})

    deposit_limit = 1_000_000_000 * (10 ** (decimals))
    debt_ratio = 10_000
    
    vault.addStrategy(strategy, debt_ratio, 0, 2 ** 256 - 1, 500, {"from": gov})
    vault.setDepositLimit(deposit_limit, {"from": gov})

    assert deposit_limit == vault.depositLimit()
 
    whale_deposit = 1_000_000 * (10 ** (decimals))
    vault.deposit(whale_deposit, {"from": whale})

    strategy.harvest({"from": strategist})
   
    status = strategy.lendStatuses()
    form = "{:.2%}"
    formS = "{:,.0f}"
    for j in status:
        print(
            f"Lender: {j[0]}, Deposits: {formS.format(j[1]/1e18)}, APR: {form.format(j[2]/1e18)}"
        )
    chain.mine(20)
    scrDai.mint(0, {"from": strategist})


    vault.updateStrategyDebtRatio(strategy, 0, {"from": gov})
    strategy.harvest({"from": strategist})
    print(scrDai.balanceOf(screamPlugin))
    print(screamPlugin.hasAssets())
    chain.mine(20)
    scrDai.mint(0, {"from": strategist})
    chain.mine(10)
    strategy.harvest({"from": strategist})
    
    print(scrDai.balanceOf(screamPlugin))
    print(screamPlugin.hasAssets())
    chain.mine(20)
    scrDai.mint(0, {"from": strategist})

    chain.mine(10)
    strategy.harvest({"from": strategist})
    print(screamPlugin.hasAssets())
    print(scrDai.balanceOf(screamPlugin))
    status = strategy.lendStatuses()
    for j in status:
        print(
            f"Lender: {j[0]}, Deposits: {formS.format(j[1]/1e18)}, APR: {form.format(j[2]/1e18)}"
        )
    chain.mine(20)
    scrDai.mint(0, {"from": strategist})
    vault.updateStrategyDebtRatio(strategy, 10_000, {"from": gov})
    strategy.harvest({"from": strategist})

    strategy.harvest({"from": strategist})
    status = strategy.lendStatuses()
    for j in status:
        print(
            f"Lender: {j[0]}, Deposits: {formS.format(j[1]/1e18)}, APR: {form.format(j[2]/1e18)}"
        )


def print_lenders(strategy, decimals=6):
    form = "{:.2%}"
    formS = "{:,.2f}"

    status = strategy.lendStatuses()
    print("  Gen Lender Real APRs:")

    for j in status:
        print(
            f"    Lender: {j[0]}, Deposits: {formS.format(j[1]/(10 ** decimals))}, APR: {form.format(j[2]/(1e18))}"
        )
