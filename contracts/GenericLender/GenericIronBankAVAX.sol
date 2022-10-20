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

import "./GenericLenderBase.sol";

contract GenericIronBankAVAX is GenericLenderBase {
    using SafeERC20 for IERC20;
    using Address for address;
    using SafeMath for uint256;

    uint256 private constant blocksPerYear = 3154 * 10**4;
    address public constant router = address(0x60aE616a2155Ee3d9A68541Ba4544862310933d4);
    address public constant wavax = address(0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7);

    uint256 public dustThreshold;

    CErc20I public cToken;

    constructor(
        address _strategy,
        string memory name,
        address _cToken
    ) public GenericLenderBase(_strategy, name) {
        _initialize(_cToken);
    }

    function initialize(address _cToken) external {
        _initialize(_cToken);
    }

    function _initialize(address _cToken) internal {
        require(address(cToken) == address(0), "GenericIBAVAX already initialized");
        cToken = CErc20I(_cToken);
        require(cToken.underlying() == address(want), "WRONG CTOKEN");
        want.safeApprove(_cToken, uint256(-1));
        dustThreshold = 10_000; //depends on want
    }

    function cloneCompoundLender(
        address _strategy,
        string memory _name,
        address _cToken
    ) external returns (address newLender) {
        newLender = _clone(_strategy, _name);
        GenericIronBankAVAX(newLender).initialize(_cToken);
    }

    function nav() external view override returns (uint256) {
        return _nav();
    }

    //adjust dust threshol
    function setDustThreshold(uint256 amount) external management {
        dustThreshold = amount;
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
        return (cToken.supplyRatePerBlock()).mul(blocksPerYear);
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
        //dont care about errors here. we want to exit what we can
        uint256 amountCToken = convertFromUnderlying(amount);
        cToken.redeem(Math.min(amountCToken, cToken.balanceOf(address(this))));

        // Send to governance
        want.safeTransfer(vault.governance(), want.balanceOf(address(this)));
    }

    //withdraw an amount including any want balance
    function _withdraw(uint256 amount) internal returns (uint256) {
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

        looseBalance = want.balanceOf(address(this));
        want.safeTransfer(address(strategy), looseBalance);
        return looseBalance;
    }

    function deposit() external override management {
        uint256 balance = want.balanceOf(address(this));
        require(cToken.mint(balance) == 0, "ctoken: mint fail");
    }

    function withdrawAll() external override management returns (bool) {
        uint256 liquidity = want.balanceOf(address(cToken));
        uint256 liquidityInCTokens = convertFromUnderlying(liquidity);
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
        return cToken.balanceOf(address(this)) > dustThreshold || want.balanceOf(address(this)) > 0;
    }

    function aprAfterDeposit(uint256 amount) external view override returns (uint256) {
        uint256 cashPrior = want.balanceOf(address(cToken));

        uint256 borrows = cToken.totalBorrows();

        uint256 reserves = cToken.totalReserves();

        uint256 reserverFactor = cToken.reserveFactorMantissa();

        InterestRateModel model = cToken.interestRateModel();

        //the supply rate is derived from the borrow rate, reserve factor and the amount of total borrows.
        uint256 supplyRate = model.getSupplyRate(cashPrior.add(amount), borrows, reserves, reserverFactor);
        return supplyRate.mul(blocksPerYear);
    }

    function protectedTokens() internal view override returns (address[] memory) {}
}
