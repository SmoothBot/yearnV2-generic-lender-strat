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
import {Math} from "@openzeppelin/contracts/math/Math.sol";

import "../Interfaces/UniswapInterfaces/IUniswapV2Router02.sol";
import "../Interfaces/HundredFinance/IGuage.sol";

import "./GenericLenderBase.sol";

interface iMinter {
    function mint(address) external;
}

interface iRewardsPolicy {
    function rate_at(uint256) external view returns (uint256);
}

interface iController {
    function gauge_relative_weight(address) external view returns (uint256);
}

interface IERC20Extended is IERC20 {
    function decimals() external view returns (uint256);
    function symbol() external view returns (string memory);
}

/********************
 *   A lender plugin for LenderYieldOptimiser for any erc20 asset on compound (not eth)
 *   Made by SamPriestley.com
 *   https://github.com/Grandthrax/yearnv2/blob/master/contracts/GenericDyDx/GenericCompound.sol
 *
 ********************* */

contract GenericHundredFinance is GenericLenderBase {
    using SafeERC20 for IERC20;
    using Address for address;
    using SafeMath for uint256;

    uint256 private blocksPerYear = 30 * 60 * 24 * 365;
    address public router;
    address public hnd;
    address public weth;

    // Scale we multiply the APR by because the contract isn't boosted.
    uint256 public aprScale = 66;
    IGuage public guage;
    address public minter;
    address public rewards_policy;
    address public controller;

    uint256 public dustThreshold;

    bool public ignorePrinting;

    uint256 public minIbToSell = 0 ether;

    CErc20I public cToken;

    constructor(
        address _strategy,
        string memory name,
        address _cToken,
        address _guage,
        address _weth, 
        address _router,
        address _hnd
    ) public GenericLenderBase(_strategy, name) {
        _initialize(_cToken, _guage, _weth, _router, _hnd);
    }

    function initialize(address _cToken, address _guage, address _weth, address _router, address _hnd) external {
        _initialize(_cToken, _guage, _weth, _router, _hnd);
    }

    function _initialize(address _cToken, address _guage, address _weth, address _router, address _hnd) internal {
        require(address(cToken) == address(0), "GenericIB already initialized");
        router = _router;
        hnd = _hnd;
        weth = _weth;
        cToken = CErc20I(_cToken);
        guage = IGuage(_guage);
        _setupSecondaryContract();
        require(cToken.underlying() == address(want), "WRONG CTOKEN");
        want.safeApprove(_cToken, uint256(-1));
        cToken.approve(_guage, uint256(-1));
        IERC20(hnd).safeApprove(router, uint256(-1));
        // IERC20(weth).safeApprove(router, uint256(-1));
        dustThreshold = 1_000_000_000; //depends on want
    }

    function cloneCompoundLender(
        address _strategy,
        string memory _name,
        address _cToken,
        address _guage,
        address _weth, 
        address _router,
        address _hnd
    ) external returns (address newLender) {
        newLender = _clone(_strategy, _name);
        GenericHundredFinance(newLender).initialize(_cToken, _guage, _weth, _router, _hnd);
    }

    function nav() external view override returns (uint256) {
        return _nav();
    }

    //adjust dust threshol
    function setDustThreshold(uint256 amount) external management {
        dustThreshold = amount;
    }

    // Adjust blocks per year - this is to support different chains.
    function setBlocksPerYear(uint256 _blocksPerYear) external management {
        blocksPerYear = _blocksPerYear;
    }

    //adjust dust threshol
    function setAPRScalar(uint256 scale) external management {
        require(scale >= 0 && scale <= 100, "!invalid scale");
        aprScale = scale;
    }

    function setGuage(address _guage) external govOnly {
        guage = IGuage(_guage);
        _setupSecondaryContract();
    }

    function _setupSecondaryContract() internal {
        if (address(guage) != address(0)) {
            controller = guage.controller();
            minter = guage.minter();
            rewards_policy = guage.reward_policy_maker();
        }
    }

    function setMinIbToSellThreshold(uint256 amount) external management {
        minIbToSell = amount;
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
        uint256 currentCr = cToken.balanceOf(address(this));
        currentCr = currentCr.add(guage.balanceOf(address(this)));
        if (currentCr < dustThreshold) {
            balance = 0;
        } else {
            //The current exchange rate as an unsigned integer, scaled by 1e18.
            balance = currentCr.mul(cToken.exchangeRateStored()).div(1e18);
        }
    }

    function apr() external view override returns (uint256) {
        return _apr();
    }

    function _apr() internal view returns (uint256) {
        return (cToken.supplyRatePerBlock().add(guageAPR(0)));
    }

    function guageAPR(uint256 change) public view returns (uint256) {
        if (ignorePrinting || minter == address(0)) {
            return 0;
        }

        uint256 guage_weight = iController(controller).gauge_relative_weight(address(guage));
        uint256 guage_working_supply = guage.working_supply().mul(cToken.exchangeRateStored()).div(1e18);
        guage_working_supply = guage_working_supply.add(change);
        if (guage_working_supply == 0) {
            return 0;
        }

        uint256 rewards_rate = iRewardsPolicy(rewards_policy).rate_at(block.timestamp);
        uint256 exchangeRate = priceCheck(hnd, address(want), 1e18);
        uint256 per_year = blocksPerYear.mul(rewards_rate).mul(guage_weight).div(1e18);
        uint256 compRate;
        if (per_year != 0) {
            compRate = per_year.mul(exchangeRate).div(guage_working_supply);
            // scale by aprScale % because we have no veHND
            compRate = compRate.mul(aprScale).div(100);
        }

        return (compRate);
    }

    // WARNING. manipulatable and simple routing. Only use for safe functions
    function priceCheck(
        address start,
        address end,
        uint256 _amount
    ) public view returns (uint256) {
        if (_amount == 0) {
            return 0;
        }
        address[] memory path = getTokenOutPath(start, end);
        uint256[] memory amounts = IUniswapV2Router02(router).getAmountsOut(_amount, path);

        return amounts[amounts.length - 1];
    }

    function weightedApr() external view override returns (uint256) {
        uint256 a = _apr();
        return a.mul(_nav());
    }

    function withdraw(uint256 amount) external override management returns (uint256) {
        return _withdraw(amount);
    }

    // Emergency withdraw. sends balance plus amount to governance
    function emergencyWithdraw(uint256 amount) external override management {
        uint256 amountInGauge = guage.balanceOf(address(this));
        if (amountInGauge > 0) {
            guage.withdraw(amountInGauge);
        }
    
        //dont care about errors here. we want to exit what we can
        uint256 amountCToken = convertFromUnderlying(amount);
        cToken.redeem(Math.min(amountCToken, cToken.balanceOf(address(this))));

        // Send to governance
        want.safeTransfer(vault.governance(), want.balanceOf(address(this)));
    }

    //withdraw an amount including any want balance
    function _withdraw(uint256 amount) internal returns (uint256) {
        uint256 amountInGauge = guage.balanceOf(address(this));
        if (amountInGauge > 0) {
            guage.withdraw(amountInGauge);
        }

        uint256 balanceUnderlying = cToken.balanceOfUnderlying(address(this));
        uint256 looseBalance = want.balanceOf(address(this));
        uint256 total = balanceUnderlying.add(looseBalance);

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
            return amount;
        }

        //not state changing but OK because of previous call
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
        guage.deposit(cToken.balanceOf(address(this)));

        return looseBalance;
    }

    function manualClaimAndDontSell() external management {
        iMinter(minter).mint(address(guage));
    }

    // Spookyswap is best for hnd/weth. we check if there is a better path for the second lot
    function _disposeOfComp() internal {
        if (minter != address(0)) {
            iMinter(minter).mint(address(guage));
            uint256 _ib = IERC20(hnd).balanceOf(address(this));

            if (_ib > minIbToSell) {
                address[] memory path = getTokenOutPath(hnd, address(want));
                IUniswapV2Router02(router).swapExactTokensForTokens(_ib, uint256(0), path, address(this), now);
            }
        }
    }

    function getTokenOutPath(address _token_in, address _token_out) internal view returns (address[] memory _path) {
        bool is_weth = _token_in == address(weth) || _token_out == address(weth);
        _path = new address[](is_weth ? 2 : 3);
        _path[0] = _token_in;
        if (is_weth) {
            _path[1] = _token_out;
        } else {
            _path[1] = address(weth);
            _path[2] = _token_out;
        }
    }

    function deposit() external override management {
        uint256 balance = want.balanceOf(address(this));
        require(cToken.mint(balance) == 0, "ctoken: mint fail");

        //deposit to gauge
        guage.deposit(cToken.balanceOf(address(this)));
    }

    function withdrawAll() external override management returns (bool) {
        uint256 liquidity = want.balanceOf(address(cToken));
        uint256 liquidityInCTokens = convertFromUnderlying(liquidity);
        uint256 amountInGauge = guage.balanceOf(address(this));
        if (amountInGauge > 0) {
            guage.withdraw(amountInGauge);
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

    function hasAssets() external view override returns (bool) {
        //return cToken.balanceOf(address(this)) > 0;
        return
            cToken.balanceOf(address(this)) > dustThreshold ||
            want.balanceOf(address(this)) > 0 ||
            guage.balanceOf(address(this)) > dustThreshold;
    }

    function aprAfterDeposit(uint256 amount) external view override returns (uint256) {
        uint256 cashPrior = want.balanceOf(address(cToken));

        uint256 borrows = cToken.totalBorrows();

        uint256 reserves = cToken.totalReserves();

        uint256 reserverFactor = cToken.reserveFactorMantissa();

        InterestRateModel model = cToken.interestRateModel();

        //the supply rate is derived from the borrow rate, reserve factor and the amount of total borrows.
        uint256 supplyRate = model.getSupplyRate(cashPrior.add(amount), borrows, reserves, reserverFactor);
        supplyRate = supplyRate.add(guageAPR(amount));

        return supplyRate.mul(blocksPerYear);
    }

    function protectedTokens() internal view override returns (address[] memory) {}
}
