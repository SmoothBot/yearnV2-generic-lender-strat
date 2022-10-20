import brownie
import pytest
from brownie import ZERO_ADDRESS, interface, accounts
import conftest as config

@pytest.fixture
def qi_whale():
    return accounts.at('0x9f8c163cba728e99993abe7495f06c0a3c8ac8b9', True)

@pytest.fixture
def wavax_whale():
    return accounts.at('0x0c91a070f862666bbcce281346be45766d874d98', True)

@pytest.fixture
def qi_comp():
    return interface.IERC20Extended('0x8729438EB15e2C8B576fCc6AeCdA6A148776C0F5')

@pytest.fixture
def wavax():
    return interface.IERC20Extended('0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7')

@pytest.mark.parametrize(config.fixtures, config.params, indirect=True)
def test_selling_aave(
    strategyAddAave, token, aToken, qiToken, chain, whale, vault, strategy, gov, strategist, lenders, amount, decimals, lenderAave, wavax_whale, wavax
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
    assert strategy.harvestTrigger(1) == True
    print(whale_deposit / 1e18)
    status = strategy.lendStatuses()
    form = "{:.2%}"
    formS = "{:,.0f}"
    for j in status:
        print(
            f"Lender: {j[0]}, Deposits: {formS.format(j[1]/(10 ** decimals))} APR: {form.format(j[2]/1e18)}"
        )

    strategy.harvest({"from": strategist})
    
    # Start of selling test
    wavax.transfer(lenderAave, 100 * 1e18, {'from': wavax_whale})
    amount0 = wavax.balanceOf(lenderAave)
    print(amount0)

    lenderAave.harvest({'from': gov})
    #lenderAave.withdraw(1, {'from': gov})
    print(wavax.balanceOf(lenderAave))
    assert wavax.balanceOf(lenderAave) < amount0


@pytest.mark.parametrize(config.fixtures, config.params, indirect=True)
def test_selling_benqi_avax(
    strategyAddBenqi, token, aToken, qiToken, chain, whale, vault, strategy, gov, strategist, lenders, amount, decimals, lenderBenqi, wavax_whale, wavax
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
    assert strategy.harvestTrigger(1) == True
    print(whale_deposit / 1e18)
    status = strategy.lendStatuses()
    form = "{:.2%}"
    formS = "{:,.0f}"
    for j in status:
        print(
            f"Lender: {j[0]}, Deposits: {formS.format(j[1]/(10 ** decimals))} APR: {form.format(j[2]/1e18)}"
        )

    strategy.harvest({"from": strategist})
    
    # Start of selling test
    wavax.transfer(lenderBenqi, 100 * 1e18, {'from': wavax_whale})
    amount0 = wavax.balanceOf(lenderBenqi)
    print(amount0)

    lenderBenqi.withdraw(10 ** (decimals - 4), {'from': gov})

    print(wavax.balanceOf(lenderBenqi))
    assert wavax.balanceOf(lenderBenqi) < amount0


@pytest.mark.parametrize(config.fixtures, config.params, indirect=True)
def test_selling_benqi_comp(
    strategyAddBenqi, token, aToken, qiToken, chain, whale, vault, strategy, gov, strategist, lenders, amount, decimals, lenderBenqi, qi_whale, qi_comp
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
    assert strategy.harvestTrigger(1) == True
    print(whale_deposit / 1e18)
    status = strategy.lendStatuses()
    form = "{:.2%}"
    formS = "{:,.0f}"
    for j in status:
        print(
            f"Lender: {j[0]}, Deposits: {formS.format(j[1]/(10 ** decimals))} APR: {form.format(j[2]/1e18)}"
        )

    strategy.harvest({"from": strategist})
    
    # Start of selling test
    qi_comp.transfer(lenderBenqi, 100 * 1e18, {'from': qi_whale})
    amount0 = qi_comp.balanceOf(lenderBenqi)
    print(amount0)

    lenderBenqi.withdraw(10 ** (decimals - 4) , {'from': gov})

    print(qi_comp.balanceOf(lenderBenqi))
    assert qi_comp.balanceOf(lenderBenqi) < amount0

