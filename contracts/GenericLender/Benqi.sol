// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

import "../Interfaces/Compound/InterestRateModel.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/math/SafeMath.sol";
import "@openzeppelin/contracts/utils/Address.sol";
import "@openzeppelin/contracts/token/ERC20/SafeERC20.sol";

import "../Interfaces/UniswapInterfaces/IUniswapV2Router02.sol";

import "../Interfaces/Benqi/CErc20TimestampI.sol";
import "../Interfaces/Benqi/ComptrollerBenqiInterface.sol";
import "../Interfaces/utils/IWavax.sol";
import "./GenericLenderBase.sol";

/********************
 *   A lender plugin for LenderYieldOptimiser for any erc20 asset on compound (not eth)
 *   Made by SamPriestley.com
 *   https://github.com/Grandthrax/yearnv2/blob/master/contracts/GenericDyDx/GenericCompound.sol
 *
 ********************* */

contract Benqi is GenericLenderBase {
    using SafeERC20 for IERC20;
    using Address for address;
    using SafeMath for uint256;

    uint256 private constant blocksPerYear = 31_557_600;
    address public constant uniswapRouter = address(0x60aE616a2155Ee3d9A68541Ba4544862310933d4);
    address public constant comp = address(0x8729438EB15e2C8B576fCc6AeCdA6A148776C0F5);
    address public constant wavax = address(0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7);
    address public constant unitroller = address(0x486Af39519B4Dc9a7fCcd318217352830E8AD9b4);


    uint256 public dustThreshold;

    uint256 public minCompToSell = 1 ether;
    uint256 public minAvaxToSell = 0.01 ether;

    CErc20TimestampI public cToken;

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
        require(address(cToken) == address(0), "Benqi already initialized");
        cToken = CErc20TimestampI(_cToken);
        require(cToken.underlying() == address(want), "WRONG CTOKEN");
        want.safeApprove(_cToken, uint256(-1));
        IERC20(comp).safeApprove(uniswapRouter, uint256(-1));
        IERC20(wavax).safeApprove(uniswapRouter, uint256(-1));
        dustThreshold = 10_000;
    }

    receive() external payable {}


    function cloneBenqiLender(
        address _strategy,
        string memory _name,
        address _cToken
    ) external returns (address payable newLender) {
        newLender = payable(_clone(_strategy, _name));
        Benqi(newLender).initialize(_cToken);
    }

    //adjust dust threshol
    function setDustThreshold(uint256 amount) external management {
        dustThreshold = amount;
    }

    function setMinCompToSell(uint256 amount) external management {
        minCompToSell = amount;
    }

    function setMinAvaxToSell(uint256 amount) external management {
        minAvaxToSell = amount;
    }

    function nav() external view override returns (uint256) {
        return _nav();
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
        return (cToken.supplyRatePerTimestamp().add(compBlockShareInWant(0, false))).mul(blocksPerYear);
    }

    function compBlockShareInWant(uint256 change, bool add) public view returns (uint256) {
        //QI tokens
        //comp speed is amount to borrow or deposit (so half the total distribution for want)
        uint256 compDistributionPerBlock = ComptrollerBenqiInterface(unitroller).supplyRewardSpeeds(0, address(cToken));
        uint256 wavaxDistributionPerBlock = ComptrollerBenqiInterface(unitroller).supplyRewardSpeeds(1, address(cToken));

        //convert to per dolla
        uint256 totalSupply = cToken.totalSupply().mul(cToken.exchangeRateStored()).div(1e18);
        if (add) {
            totalSupply = totalSupply.add(change);
        } else {
            totalSupply = totalSupply.sub(change);
        }

        uint256 compShareSupply = 0;
        uint256 wavaxShareSupply = 0;
        if (totalSupply > 0) {
            compShareSupply = compDistributionPerBlock.mul(1e18).div(totalSupply);
            wavaxShareSupply = wavaxDistributionPerBlock.mul(1e18).div(totalSupply);
        }

        uint256 estimatedWantFromComp = priceCheck(comp, address(want), compShareSupply);
        uint256 estimatedWantFromWavax = priceCheck(wavax, address(want), wavaxShareSupply);
        uint256 compRate;
        uint256 wavaxRate;
        if (estimatedWantFromComp != 0) {
            compRate = estimatedWantFromComp.mul(9).div(10); //10% pessimist
        }
        if (estimatedWantFromWavax != 0) {
            wavaxRate = estimatedWantFromWavax.mul(9).div(10); //10% pessimist
        }

        return (compRate.add(wavaxRate));
    }

    function priceCheck(
        address start,
        address end,
        uint256 _amount
    ) public view returns (uint256) {
        if (_amount == 0) {
            return 0;
        }
        address[] memory path = getTokenOutPath(start, end);
        uint256[] memory amounts = IUniswapV2Router02(uniswapRouter).getAmountsOut(_amount, path);

        return amounts[amounts.length - 1];
    }


    function weightedApr() external view override returns (uint256) {
        uint256 a = _apr();
        return a.mul(_nav());
    }

    function withdraw(uint256 amount) external override management returns (uint256) {
        return _withdraw(amount);
    }

    //emergency withdraw. sends balance plus amount to governance
    function emergencyWithdraw(uint256 amount) external override management {
        //dont care about errors here. we want to exit what we can
        cToken.redeemUnderlying(amount);

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
        _disposeOfComp();
        looseBalance = want.balanceOf(address(this));
        want.safeTransfer(address(strategy), looseBalance);
        return looseBalance;
    }

    function _disposeOfComp() internal {
        ComptrollerBenqiInterface comptroller = ComptrollerBenqiInterface(unitroller);

        comptroller.claimReward(0, payable(address(this)));
        comptroller.claimReward(1, payable(address(this)));
        uint256 _comp = IERC20(comp).balanceOf(address(this));

        if (_comp > minCompToSell) {
            address[] memory path1 = getTokenOutPath(comp, address(want));
            IUniswapV2Router02(uniswapRouter).swapExactTokensForTokens(_comp, uint256(0), path1, address(this), block.timestamp);
        }
        IWavax(payable(wavax)).deposit{value: address(this).balance}();
        uint256 _avax = IERC20(wavax).balanceOf(address(this));
        if (_avax > minAvaxToSell) {
            address[] memory path2 = getTokenOutPath(wavax, address(want));
            IUniswapV2Router02(uniswapRouter).swapExactTokensForTokens(_avax, uint256(0), path2, address(this), block.timestamp);
        }
    }

    function getTokenOutPath(address _token_in, address _token_out) internal pure returns (address[] memory _path) {
        bool is_wavax = _token_in == address(wavax) || _token_out == address(wavax);
        _path = new address[](is_wavax ? 2 : 3);
        _path[0] = _token_in;
        if (is_wavax) {
            _path[1] = _token_out;
        } else {
            _path[1] = address(wavax);
            _path[2] = _token_out;
        }
    }

    function deposit() external override management {
        uint256 balance = want.balanceOf(address(this));
        require(cToken.mint(balance) == 0, "ctoken: mint fail");
    }

    function withdrawAll() external override management returns (bool) {
        uint256 invested = _nav();
        uint256 returned = _withdraw(invested);
        return returned >= invested;
    }

    function hasAssets() external view override returns (bool) {
        //return cToken.balanceOf(address(this)) > 0;
        return cToken.balanceOf(address(this)) > 0 || want.balanceOf(address(this)) > 0;
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

    function protectedTokens() internal view override returns (address[] memory) {
        address[] memory protected = new address[](3);
        protected[0] = address(want);
        protected[1] = address(cToken);
        protected[2] = comp;
        return protected;
    }
}
