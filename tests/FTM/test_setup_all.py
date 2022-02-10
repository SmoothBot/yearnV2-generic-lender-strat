from itertools import count
from brownie import Wei, reverts
from useful_methods import genericStateOfVault, genericStateOfStrat

def test_normal_activity(
    accounts,
    Contract,
    GenericIronBank
):
    gov = accounts.at('0xC0E2830724C946a6748dDFE09753613cd38f6767', force=True)

    #yfi
    yfi_vault = Contract('0x2C850cceD00ce2b14AA9D658b7Cad5dF659493Db')
    
    old_ftm_yfi = Contract('0x7f33Db0A35D794223d46B23562aB4590fE141Cda')
    scream_plugin = Contract('0xcf86023D284751d1bbBD98554Cff0E4912553836')
    yfi_genlender = Contract('0xDf262B43bea0ACd0dD5832cf2422e0c9b2C539dc')
    #manualAll = [[old_ftm_cream, 900], [scream_plugin, 100]]
    #yfi_genlender.manualAllocation(manualAll, {"from": gov})
    #print_lenders(yfi_genlender)

    old_ftm_yfi.manualClaimAndDontSell({'from': gov})
    ibtoken = Contract('0x00a35FD824c717879BF370E70AC6868b95870Dfb')
    old_ftm_yfi.sweep(ibtoken, {'from': gov})
    print(ibtoken.balanceOf(gov))
    
    
    crYFI = Contract('0x0980f2F0D2af35eF2c4521b2342D59db575303F7')
    yfi_genlender.safeRemoveLender(old_ftm_yfi, {'from': gov})

    #liquidityMining = Contract('0xa9d61326709B5C2D5897e0753998DFf7F1e974Fe')
    #
    #liquidityMining.claimRewards([old_ftm_cream], [crYFI], [ibtoken], False, True, {'from': gov})
    #print(ibtoken.balanceOf(old_ftm_cream))
    #old_ftm_cream.sweep(ibtoken, {'from': gov})
    #print(ibtoken.balanceOf(gov))
    #spooky = Contract('0xF491e7B69E4244ad4002BC14e878a34207E38c29')
    #ibtoken.approve(spooky, 2**256-1, {'from': gov})
    #yfi = Contract('0x29b0Da86e484E1C0029B56e817912d778aC0EC69')
    #print(yfi.balanceOf(yfi_genlender))
    #wftm = Contract('0x21be370D5312f44cB42ce377BC9b8a0cEF1A4C83')
    #path = [ibtoken, wftm, yfi]
    #inamount = ibtoken.balanceOf(gov)
    #out = spooky.getAmountsOut(inamount, path)[2]*0.90
    #spooky.swapExactTokensForTokens(inamount, out, path, yfi_genlender, 2**256-1, {'from': gov})
    #print(yfi.balanceOf(yfi_genlender))
    #print(ibtoken.balanceOf(gov))

  
    #yfi_genlender.addLender(ibPlugin, {'from': gov})
    #tx = yfi_genlender.harvest({"from": gov})
    #print(tx.events)
    #print_lenders(yfi_genlender)

    ibPlugin = gov.deploy(GenericIronBank, yfi_genlender, "IB Lender YFI", crYFI)
    ibPlugin.setUseSpirit(True)
    ibtoken.transfer(ibPlugin, ibtoken.balanceOf(gov), {"from": gov})
    print(ibtoken.balanceOf(ibPlugin))
    yfi_genlender.addLender(ibPlugin, {'from': gov})
    manualAll = [[ibPlugin, 1000]]
    yfi_genlender.manualAllocation(manualAll, {"from": gov})
    print_lenders(yfi_genlender)
    yfi_genlender.setWithdrawalThreshold(0,{"from": gov})
    tx = yfi_genlender.harvest({"from": gov})
    print(tx.events)
    print(ibtoken.balanceOf(ibPlugin))

    #dai
    #dai_vault = Contract('0x637eC617c86D24E421328e6CAEa1d92114892439')
    #dai_genlender = Contract('0xd025b85db175ef1b175af223bd37f330db277786')
    #old_ftm_cream = Contract('0x776C0Bd1438290fB97781309B18Cd96B78548688')
    #crDAI = Contract('0x04c762a5dF2Fa02FE868F25359E0C259fB811CfE')
    #dai_genlender.safeRemoveLender(old_ftm_cream, {'from': gov})

    #ibPlugin = GenericIronBank.at('0xB8507109d1e87fb5bcfB2ac52CDd5f9e39eA26f3')
    #tx = ibPlugin.cloneCompoundLender(dai_genlender, "IB Lender DAI", crDAI, {'from': gov})
    #ibPlugin = gov.deploy(GenericIronBank, dai_genlender, "IB Lender DAI", crDAI)
    #ibPlugin = GenericIronBank.at(tx.return_value)
    #dai_genlender.addLender(ibPlugin, {'from': gov})
    #manualAll = [[ibPlugin, 1000]]
    #dai_genlender.manualAllocation(manualAll, {"from": gov})
    
    #print_lenders(dai_genlender)

    #wftm
    #wftm_vault = Contract('0x0DEC85e74A92c52b7F708c4B10207D9560CEFaf0')
    #wftm_genlender = Contract('0x695A4a6e5888934828Cb97A3a7ADbfc71A70922D')
    #old_ftm_cream = Contract('0xAc3Fb94061FFfa8A459586Fa7d90fa0d6B8cd0e6')
    #crWFTM = Contract('0xd528697008aC67A21818751A5e3c58C8daE54696')
    #wftm_genlender.safeRemoveLender(old_ftm_cream, {'from': gov})

    #ibPlugin = gov.deploy(GenericIronBank, wftm_genlender, "IB Lender WFTM", crWFTM)
    #ibPlugin = GenericIronBank.at('0xB8507109d1e87fb5bcfB2ac52CDd5f9e39eA26f3')
    #wftm_genlender.addLender(ibPlugin, {'from': gov})
    #manualAll = [[ibPlugin, 1000]]
    #wftm_genlender.manualAllocation(manualAll, {"from": gov})

    #oxdao = Contract('0x585d4024c6ab31b67dfd1624f2ca01eb1dbe8d22')

    #wftm_vault.updateStrategyDebtRatio(oxdao, 7875, {"from": gov})  
    #wftm_vault.updateStrategyDebtRatio(wftm_genlender, 1000, {"from": gov}) 

    #oxdao.harvest({"from": gov})
    #wftm_genlender.setDoHealthCheck(False,{"from": gov})
    #wftm_genlender.harvest({"from": gov})

    #print_lenders(wftm_genlender)

def test_yfi_hundred(accounts,
    Contract,
    GenericHundredFinance,
    GenericCream):
    gov = accounts.at('0xC0E2830724C946a6748dDFE09753613cd38f6767', force=True)

    hUSDCguage = Contract('0x110614276F7b9Ae8586a1C1D9Bc079771e2CE8cF')
    hUSDC = Contract('0x243E33aa7f6787154a8E59d3C27a66db3F8818ee')
    usdc = Contract('0x04068DA6C83AFCFA0e13ba15A6696662335D5B75')
    usdc_whale = accounts.at('0x93C08a3168fC469F3fC165cd3A471D19a37ca19e', force=True)

    #yfi_genlender = Contract('0xDf262B43bea0ACd0dD5832cf2422e0c9b2C539dc')
    #genericCream = Contract('0x5A1cB716a389b8F8658D5d471391E530C3e570AA')

    #tx = genericCream.cloneCreamLender(yfi_genlender, "Hundred Lender YFI", hYFI, {'from': gov})
    #hPlugin = GenericCream.at(tx.return_value)
    #hPlugin = GenericCream.at('0xF4D1Ab2169eaC23043519cABcf211ec7259dbc7c')
    #yfi_genlender.addLender(hPlugin, {'from': gov})

    usdc_hundred_finance = GenericHundredFinance.deploy(strategy, )

    yfi_vault = Contract('0x2C850cceD00ce2b14AA9D658b7Cad5dF659493Db')
    

    vedao = Contract('0x6a59081C7d5ac3e82c58D5f595ed25D55E71EBDa')
    yfi_vault.updateStrategyDebtRatio(yfi_genlender, 500, {"from": gov})  
    yfi_vault.updateStrategyDebtRatio(vedao, 9500, {"from": gov}) 
    
    
    geniron = '0x07D635b3Cb3F63d6ae20720748f1A3eAaf3e8903'
    print_lenders(yfi_genlender)
    yfi_genlender.harvest({"from": gov})
    vedao.harvest({"from": gov})
    

    #manualAll = [[hPlugin, 500], [geniron, 500]]
    #yfi_genlender.manualAllocation(manualAll, {"from": gov})

    #yfi_genlender.setKeeper('0x59e5C0BA3008E85F0cA59586EbC399bC1F47a42B', {"from": gov})
    
    print_lenders(yfi_genlender)





def print_lenders(strategy, decimals=18):
    form = "{:.2%}"
    formS = "{:,.2f}"

    status = strategy.lendStatuses()
    print("  Gen Lender Real APRs:")

    for j in status:
        print(
            f"    Lender: {j[0]}, Deposits: {formS.format(j[1]/(10 ** decimals))}, APR: {form.format(j[2]/(1e18))}"
        )
