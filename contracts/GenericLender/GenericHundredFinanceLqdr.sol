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
import "../Interfaces/HundredFinance/IGuage.sol";

import "./GenericLenderBase.sol";

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
    address public constant hnd = address(0x10010078a54396F62c96dF8532dc2B4847d47ED3);
    address public constant wftm = address(0x21be370D5312f44cB42ce377BC9b8a0cEF1A4C83);
    


    // IGuage public guage;
    address public minter;
    address public rewards_policy;
    address public controller;

    uint256 public dustThreshold;

    bool public ignorePrinting;

    bool public useSpirit;

    uint256 public minIbToSell = 0 ether;

    CErc20I public cToken;
    ILiquidHundredChef public chef;
    IGuage public guage;
    uint256 public pid;
    
    constructor(
        address _strategy,
        string memory name,
        address _cToken,
        address _guage,
        address _chef,
        uint256 _pid
    ) public GenericLenderBase(_strategy, name) {
        _initialize(_cToken, _guage, _chef, _pid);
    }

    function initialize(address _cToken, address _guage, address _chef, uint256 _pid) public {
        _initialize(_cToken, _guage, _chef, _pid);
    }

    function _initialize(address _cToken, address _guage, address _chef, uint256 _pid) internal {
        require(address(cToken) == address(0), "Generic HND LQDR already initialized");
        cToken = CErc20I(_cToken);
        guage = IGuage(_guage);
        chef = ILiquidHundredChef(_chef);
        pid = _pid;

        // Check the cToken has the correct underlying
        require(cToken.underlying() == address(want), "WRONG CTOKEN");

        // Check PID matched
        require(chef.lpToken(_pid) == address(_cToken), "WRONG PID");

        want.safeApprove(_cToken, uint256(-1));
        cToken.approve(address(chef), uint256(-1));

        IERC20(hnd).safeApprove(spookyRouter, uint256(-1));
        IERC20(wftm).safeApprove(spiritRouter, uint256(-1));
        dustThreshold = 1_000_000_000; //depends on want
    }

    function cloneCompoundLender(
        address _strategy,
        string memory _name,
        address _cToken,
        address _guage,
        address _chef,
        uint256 _pid
    ) external returns (address newLender) {
        newLender = _clone(_strategy, _name);
        GenericHundredFinanceLqdr(newLender).initialize(_cToken, _guage, _chef, _pid);
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

    function underlyingBalanceStored() public view returns (uint256 _balance) {
        uint256 cTokenTotal = cToken.balanceOf(address(this));
        cTokenTotal = cTokenTotal.add(cTokenStaked());
        if (cTokenTotal < dustThreshold) {
            _balance = 0;
        } else {
            // The current exchange rate as an unsigned integer, scaled by 1e18.
            _balance = cTokenToWant(cTokenTotal);
            // _balance = cTokenTotal.mul(cToken.exchangeRateStored()).div(1e18);
        }
    }

    function apr() external view override returns (uint256) {
        return _apr();
    }

    function _apr() internal view returns (uint256) {
        return cToken.supplyRatePerBlock().add(guageAPR());
    }

    function guageAPR() public view returns (uint256) {
        if (ignorePrinting) {
            return 0;
        }

        uint256 poolTotal = guage.balanceOf(chef.liHNDStrategy());
        uint256 tokensPerSecond = chef.tokenPerSecond();
        uint256 wantTokenPerSecond = priceCheck(hnd, address(want), tokensPerSecond);
        uint256 compRate = wantTokenPerSecond.mul(blocksPerYear).mul(1e18).div(cTokenToWant(poolTotal));
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
        chef.emergencyWithdraw(pid, address(this));

        // dont care about errors here. we want to exit what we can
        cToken.redeem(amount);

        // Send to governance
        want.safeTransfer(vault.governance(), want.balanceOf(address(this)));
    }

    // emergency withdraw. sends balance plus amount to governance
    function emergencyWithdrawAll() external management {
        // Emergency withdraw from masterchef
        chef.emergencyWithdraw(pid, address(this));

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
            chef.deposit(pid, cToken.balanceOf(address(this)), address(this));
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
        chef.deposit(pid, _cTokenAmount, address(this));
    }

    function unstakeCToken(uint256 _cTokenAmount) internal {
        chef.withdraw(pid, _cTokenAmount, address(this));
    }

    function claim() internal {
        chef.harvest(pid, address(this));
    }

    function manualClaimAndDontSell() external management {
        claim();
    }

    //spookyswap is best for hnd/wftm. we check if there is a better path for the second lot
    function _disposeOfComp() internal {
        claim();
        uint256 _ib = IERC20(hnd).balanceOf(address(this));

        if (_ib > minIbToSell) {
            if (useSpirit) {
                address[] memory path = getTokenOutPath(hnd, wftm);
                IUniswapV2Router02(spookyRouter).swapExactTokensForTokens(_ib, uint256(0), path, address(this), now);

                path = getTokenOutPath(wftm, address(want));
                uint256 _wftm = IERC20(wftm).balanceOf(address(this));
                IUniswapV2Router02(spiritRouter).swapExactTokensForTokens(_wftm, uint256(0), path, address(this), now);
            } else {
                address[] memory path = getTokenOutPath(hnd, address(want));
                IUniswapV2Router02(spookyRouter).swapExactTokensForTokens(_ib, uint256(0), path, address(this), now);
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
        chef.deposit(pid, cToken.balanceOf(address(this)), address(this));
    }

    function withdrawAll() external override management returns (bool) {
        uint256 liquidity = want.balanceOf(address(cToken));
        uint256 liquidityInCTokens = cTokenToWant(liquidity);
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
                liquidityInCTokens = cTokenToWant(want.balanceOf(address(cToken)));
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

    function wantToCToken(uint256 amountWant) public view returns (uint256 balance) {
        if (amountWant == 0) {
            balance = 0;
        } else {
            balance = amountWant.mul(1e18).div(cToken.exchangeRateStored());
        }
    }

    function cTokenToWant(uint256 amountCToken) public view returns (uint256 balance) {
        balance = amountCToken.mul(cToken.exchangeRateStored()).div(1e18);
    }

    function cTokenStaked() public view returns (uint256) {
        return chef.userInfo(pid, address(this)).amount;
    }

    function wantStaked() public view returns (uint256) {
        return cTokenToWant(cTokenStaked());
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

        // TODO - This ignores the impact `amount` will have on the APR. Will need to be fixed.
        supplyRate = supplyRate.add(guageAPR());

        return supplyRate.mul(blocksPerYear);
    }

    function protectedTokens() internal view override returns (address[] memory) {}
}
