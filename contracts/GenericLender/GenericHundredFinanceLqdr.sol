// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

import "../Interfaces/Compound/CErc20I.sol";
import "../Interfaces/Compound/ComptrollerI.sol";
import "../Interfaces/Compound/InterestRateModel.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/math/SafeMath.sol";
import "@openzeppelin/contracts/utils/Address.sol";
import "@openzeppelin/contracts/token/ERC20/SafeERC20.sol";

import "../Interfaces/UniswapInterfaces/IUniswapV2Router02.sol";
import "../Interfaces/HundredFinance/ILiquidHundredChef.sol";

import "./GenericLenderBase.sol";

// interface iGuage is IERC20 {
//     function claimRewards(
//         address[] memory holders,
//         address[] memory cTokens,
//         address[] memory rewards,
//         bool borrowers,
//         bool suppliers
//     ) external;

//     function rewardSupplySpeeds(address, address)
//         external
//         view
//         returns (
//             uint256,
//             uint256,
//             uint256
//         );

//     function rewardTokensMap(address) external view returns (bool);

//     function deposit(uint256) external;

//     function withdraw(uint256) external;

//     function minter() external view returns (address);

//     function controller() external view returns (address);

//     function reward_policy_maker() external view returns (address);

//     function working_supply() external view returns (uint256);

//     function inflation_rate() external view returns (uint256);
// }

// interface iMinter {
//     function mint(address) external;
// }

// interface iRewardsPolicy {
//     function rate_at(uint256) external view returns (uint256);
// }

// interface iController {
//     function gauge_relative_weight(address) external view returns (uint256);
// }

// interface IERC20Extended {
//     function decimals() external view returns (uint256);
// }

/********************
 *   A lender plugin for LenderYieldOptimiser for any erc20 asset on compound (not eth)
 *   Made by SamPriestley.com
 *   https://github.com/Grandthrax/yearnv2/blob/master/contracts/GenericDyDx/GenericCompound.sol
 *
 ********************* */

contract GenericHundredFinanceLqdr is GenericLenderBase {
    using SafeERC20 for IERC20;
    using Address for address;
    using SafeMath for uint256;

    uint256 private constant blocksPerYear = 60 * 60 * 24 * 365;
    address public constant spookyRouter = address(0xF491e7B69E4244ad4002BC14e878a34207E38c29);
    address public constant spiritRouter = address(0x16327E3FbDaCA3bcF7E38F5Af2599D2DDc33aE52);
    address public constant lqdr = address(0x10b620b2dbAC4Faa7D7FFD71Da486f5D44cd86f9);
    address public constant wftm = address(0x21be370D5312f44cB42ce377BC9b8a0cEF1A4C83);
    
    ILiquidHundredChef public constant CHEF = ILiquidHundredChef(0x9A07fB107b9d8eA8B82ECF453Efb7cFb85A66Ce9);


    // iGuage public guage;
    address public minter;
    address public rewards_policy;
    address public controller;

    uint256 public dustThreshold;

    bool public ignorePrinting;

    bool public useSpirit;

    uint256 public minIbToSell = 0 ether;

    CErc20I public cToken;
    uint256 public pid;
    
    constructor(
        address _strategy,
        string memory name,
        address _cToken,
        uint256 _pid
    ) public GenericLenderBase(_strategy, name) {
        _initialize(_cToken, _pid);
    }

    function initialize(address _cToken, uint256 _pid) public {
        _initialize(_cToken, _pid);
    }

    function _initialize(address _cToken, uint256 _pid) internal {
        require(address(cToken) == address(0), "Generic HND LQDR already initialized");
        cToken = CErc20I(_cToken);
        pid = _pid;

        // Check the cToken has the correct underlying
        require(cToken.underlying() == address(want), "WRONG CTOKEN");

        // Check PID matched
        require(CHEF.lpToken(_pid) == address(_cToken), "WRONG PID");

        want.safeApprove(_cToken, uint256(-1));
        cToken.approve(address(CHEF), uint256(-1));

        IERC20(lqdr).safeApprove(spookyRouter, uint256(-1));
        IERC20(wftm).safeApprove(spiritRouter, uint256(-1));
        dustThreshold = 1_000_000_000; //depends on want
    }

    function cloneCompoundLender(
        address _strategy,
        string memory _name,
        address _cToken,
        uint256 _pid
    ) external returns (address newLender) {
        newLender = _clone(_strategy, _name);
        GenericHundredFinanceLqdr(newLender).initialize(_cToken, _pid);
    }

    function nav() external view override returns (uint256) {
        return _nav();
    }

    //adjust dust threshol
    function setDustThreshold(uint256 amount) external management {
        dustThreshold = amount;
    }

    function setMinIbToSellThreshold(uint256 amount) external management {
        minIbToSell = amount;
    }

    function setUseSpirit(bool _useSpirit) external management {
        useSpirit = _useSpirit;
    }

    //adjust dust threshol
    function setIgnorePrinting(bool _ignorePrinting) external management {
        ignorePrinting = _ignorePrinting;
    }

    function _nav() internal view returns (uint256) {
        uint256 amount = want.balanceOf(address(this)).add(underlyingBalanceStored());

        if (amount < dustThreshold) {
            return 0;
        } else {
            return amount;
        }
    }

    function underlyingBalanceStored() public view returns (uint256 balance) {
        uint256 cTokenTotal = cToken.balanceOf(address(this));
        cTokenTotal = cTokenTotal.add(cTokenStaked());
        if (cTokenTotal < dustThreshold) {
            balance = 0;
        } else {
            // The current exchange rate as an unsigned integer, scaled by 1e18.
            balance = cTokenTotal.mul(cToken.exchangeRateStored()).div(1e18);
        }
    }

    function apr() external view override returns (uint256) {
        return _apr();
    }

    function _apr() internal view returns (uint256) {
        return (cToken.supplyRatePerBlock().add(compBlockShareInWant(0, false))).mul(blocksPerYear);
    }

    function compBlockShareInWant(uint256 change, bool add) public view returns (uint256) {
        if (ignorePrinting || minter == address(0)) {
            return 0;
        }

        uint256 exchangeRate = priceCheck(lqdr, address(want), 1e18);

        // scale down by 0.4 to represent our no veHND
        //uint256 per_second = referenceStake.mul(rewards_rate).mul(guage_weight).div(guage_working_supply).mul(40).div(100);
        uint256 per_second = CHEF.tokenPerSecond();

        //uint256 estimatedWant =  priceCheck(hnd, address(want),per_second);
        uint256 compRate;
        if (per_second != 0) {
            compRate = per_second.mul(exchangeRate).div(1e18);
        }

        return (compRate);
    }


    //WARNING. manipulatable and simple routing. Only use for safe functions
    function priceCheck(
        address start,
        address end,
        uint256 _amount
    ) public view returns (uint256) {
        if (_amount == 0) {
            return 0;
        }
        address[] memory path = getTokenOutPath(start, end);
        uint256[] memory amounts = IUniswapV2Router02(spookyRouter).getAmountsOut(_amount, path);

        return amounts[amounts.length - 1];
    }

    function weightedApr() external view override returns (uint256) {
        uint256 a = _apr();
        return a.mul(_nav());
    }

    function withdraw(uint256 amount) external override management returns (uint256) {
        return _withdraw(amount);
    }

    // emergency withdraw. sends balance plus amount to governance
    function emergencyWithdraw(uint256 amount) external override management {
        // Emergency withdraw from masterchef
        CHEF.emergencyWithdraw(pid, address(this));

        // dont care about errors here. we want to exit what we can
        cToken.redeem(amount);

        // Send to governance
        want.safeTransfer(vault.governance(), want.balanceOf(address(this)));
    }

    // emergency withdraw. sends balance plus amount to governance
    function emergencyWithdrawAll() external management {
        // Emergency withdraw from masterchef
        CHEF.emergencyWithdraw(pid, address(this));

        // dont care about errors here. we want to exit what we can
        cToken.redeem(cToken.balanceOf(address(this)));

        // Send to governance
        want.safeTransfer(vault.governance(), want.balanceOf(address(this)));
    }

    // withdraw an amount including any want balance
    function _withdraw(uint256 amount) internal returns (uint256) {

        // We withdraw all from the masterchef to save us converting
        // This looks lazy, but its reduces needless complexity.
        uint256 staked = cTokenStaked();
        if (staked > 0) {
            unstakeCToken(staked);
        }

        // Calculate the total balance
        uint256 balanceUnderlying = cToken.balanceOfUnderlying(address(this));
        uint256 looseBalance = want.balanceOf(address(this));
        uint256 total = balanceUnderlying.add(looseBalance);

        // If we're trying to withdraw more than the total
        // Send everything we have
        if (amount.add(dustThreshold) >= total) {
            //cant withdraw more than we own. so withdraw all we can
            if (balanceUnderlying > dustThreshold) {
                require(cToken.redeem(cToken.balanceOf(address(this))) == 0, "ctoken: redeemAll fail");
            }

            looseBalance = want.balanceOf(address(this));
            if (looseBalance > 0) {
                want.safeTransfer(address(strategy), looseBalance);
                return looseBalance;
            } else {
                return 0;
            }
        }

        if (looseBalance >= amount) {
            want.safeTransfer(address(strategy), amount);
            CHEF.deposit(pid, cToken.balanceOf(address(this)), address(this));
            return amount;
        }

        // not state changing but OK because of previous call
        uint256 liquidity = want.balanceOf(address(cToken));
        if (liquidity > 1) {
            uint256 toWithdraw = amount.sub(looseBalance);

            if (toWithdraw > liquidity) {
                toWithdraw = liquidity;
            }
    
            if (toWithdraw > dustThreshold) {
                require(cToken.redeemUnderlying(toWithdraw) == 0, "ctoken: redeemUnderlying fail");
            }
        }

        if (!ignorePrinting) {
            _disposeOfComp();
        }

        looseBalance = want.balanceOf(address(this));
        want.safeTransfer(address(strategy), looseBalance);

        //redeposit what is left
        stakeCToken(cToken.balanceOf(address(this)));
        
        return looseBalance;
    }

    function stakeCToken(uint256 _cTokenAmount) internal {
        CHEF.deposit(pid, _cTokenAmount, address(this));
    }

    function unstakeCToken(uint256 _cTokenAmount) internal {
        CHEF.withdraw(pid, _cTokenAmount, address(this));
    }

    function claim() internal {
        CHEF.harvest(pid, address(this));
    }

    function manualClaimAndDontSell() external management {
        claim();
    }

    //spookyswap is best for hnd/wftm. we check if there is a better path for the second lot
    function _disposeOfComp() internal {
        claim();
        uint256 _ib = IERC20(lqdr).balanceOf(address(this));

        if (_ib > minIbToSell) {
            if (!useSpirit) {
                address[] memory path = getTokenOutPath(lqdr, address(want));
                IUniswapV2Router02(spookyRouter).swapExactTokensForTokens(_ib, uint256(0), path, address(this), now);
            } else {
                address[] memory path = getTokenOutPath(lqdr, wftm);
                IUniswapV2Router02(spookyRouter).swapExactTokensForTokens(_ib, uint256(0), path, address(this), now);

                path = getTokenOutPath(wftm, address(want));
                uint256 _wftm = IERC20(wftm).balanceOf(address(this));
                IUniswapV2Router02(spiritRouter).swapExactTokensForTokens(_wftm, uint256(0), path, address(this), now);
            }
        }
        
    }

    function getTokenOutPath(address _token_in, address _token_out) internal pure returns (address[] memory _path) {
        bool is_wftm = _token_in == address(wftm) || _token_out == address(wftm);
        _path = new address[](is_wftm ? 2 : 3);
        _path[0] = _token_in;
        if (is_wftm) {
            _path[1] = _token_out;
        } else {
            _path[1] = address(wftm);
            _path[2] = _token_out;
        }
    }

    function deposit() external override management {
        uint256 balance = want.balanceOf(address(this));
        require(cToken.mint(balance) == 0, "ctoken: mint fail");

        //deposit to gauge
        CHEF.deposit(pid, cToken.balanceOf(address(this)), address(this));
    }

    function withdrawAll() external override management returns (bool) {
        uint256 liquidity = want.balanceOf(address(cToken));
        uint256 liquidityInCTokens = convertFromUnderlying(liquidity);
        uint256 staked = cTokenStaked();
        if (staked > 0) {
            unstakeCToken(staked);
        }

        uint256 amountInCtokens = cToken.balanceOf(address(this));

        bool all;

        if (liquidityInCTokens > 2) {
            liquidityInCTokens = liquidityInCTokens - 1;

            if (amountInCtokens <= liquidityInCTokens) {
                //we can take all
                all = true;
                cToken.redeem(amountInCtokens);
            } else {
                //redo or else price changes
                cToken.mint(0);
                liquidityInCTokens = convertFromUnderlying(want.balanceOf(address(cToken)));
                //take all we can
                all = false;
                cToken.redeem(liquidityInCTokens);
            }
        }

        uint256 looseBalance = want.balanceOf(address(this));
        if (looseBalance > 0) {
            want.safeTransfer(address(strategy), looseBalance);
        }
        return all;
    }

    function convertFromUnderlying(uint256 amountOfUnderlying) public view returns (uint256 balance) {
        if (amountOfUnderlying == 0) {
            balance = 0;
        } else {
            balance = amountOfUnderlying.mul(1e18).div(cToken.exchangeRateStored());
        }
    }

    function cTokenStaked() public view returns (uint256) {
        return CHEF.userInfo(pid, address(this)).amount;
    }

    function wantStaked() public view returns (uint256) {
        return convertFromUnderlying(cTokenStaked());
    }

    function hasAssets() external view override returns (bool) {
        //return cToken.balanceOf(address(this)) > 0;
        return
            cToken.balanceOf(address(this)) > dustThreshold ||
            want.balanceOf(address(this)) > 0 ||
            cTokenStaked() > dustThreshold;
    }

    function aprAfterDeposit(uint256 amount) external view override returns (uint256) {
        uint256 cashPrior = want.balanceOf(address(cToken));

        uint256 borrows = cToken.totalBorrows();

        uint256 reserves = cToken.totalReserves();

        uint256 reserverFactor = cToken.reserveFactorMantissa();

        InterestRateModel model = cToken.interestRateModel();

        //the supply rate is derived from the borrow rate, reserve factor and the amount of total borrows.
        uint256 supplyRate = model.getSupplyRate(cashPrior.add(amount), borrows, reserves, reserverFactor);
        // supplyRate = supplyRate.add(compBlockShareInWant(amount, true));

        return supplyRate.mul(blocksPerYear);
    }

    function protectedTokens() internal view override returns (address[] memory) {}
}
