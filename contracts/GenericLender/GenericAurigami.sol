// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.6.12;


pragma experimental ABIEncoderV2;

import "../interfaces/Aurigami/CErc20TimestampI.sol";
import "../interfaces/Compound/InterestRateModel.sol";
import "../interfaces/UniswapInterfaces/IUniswapV2Router02.sol";
import "../interfaces/GenericLender/GenericLenderParameters.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/math/SafeMath.sol";
import "@openzeppelin/contracts/utils/Address.sol";
import "@openzeppelin/contracts/token/ERC20/SafeERC20.sol";
import "./GenericLenderBase.sol";

contract GenericAurigami is GenericLenderBase {
    using SafeERC20 for IERC20;
    using Address for address;
    using SafeMath for uint256;

    //If the protocol does not uses blocks, blocksPerYear should be set to the # of seconds in a year
    uint256 private immutable blocksPerYear;
    address public immutable uniswapRouter;
    address public immutable comp;
    address public immutable weth;
    bool public immutable usesBlocks;
    uint256 public minCompToSell = 0.5 ether;

    CErc20TimestampI public cToken;

    bool public ignorePrinting;

    constructor(
        GenericLenderParameters memory params
    ) public GenericLenderBase(params._strategy, params._name) {
        blocksPerYear = params._blocksPerYear;
        uniswapRouter = params._uniswapRouter;
        comp = params._comp;
        weth = params._weth;
        ignorePrinting = params._ignorePrinting;
        usesBlocks = params._usesBlocks;
        _initialize(params._cToken);
    }

    // TODO: this method could be removed -> only initialize the strategy with the constructor
    function initialize(address _cToken) external {
        _initialize(_cToken);
    }

    function _initialize(address _cToken) internal {
        //TODO: if initialize() is removed -> remove this require
        require(address(cToken) == address(0), "GeneriAurigami already initialized");
        cToken = CErc20TimestampI(_cToken);
        require(cToken.underlying() == address(want), "WRONG CTOKEN");
        want.safeApprove(_cToken, uint256(-1));
    }

    function cloneCompoundLender(
        address _strategy,
        string memory _name,
        address _cToken
    ) external returns (address newLender) {
        newLender = _clone(_strategy, _name);
        GenericAurigami(newLender).initialize(_cToken);
    }

    function nav() external view override returns (uint256) {
        return _nav();
    }

    function _nav() internal view returns (uint256) {
        return want.balanceOf(address(this)).add(underlyingBalanceStored());
    }

    function underlyingBalanceStored() public view returns (uint256 balance) {
        uint256 currentCr = cToken.balanceOf(address(this));
        if (currentCr == 0) {
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
        return cToken.supplyRatePerTimestamp().mul(blocksPerYear);
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

        if (amount > total) {
            //cant withdraw more than we own
            amount = total;
        }

        if (looseBalance >= amount) {
            want.safeTransfer(address(strategy), amount);
            return amount;
        }

        //not state changing but OK because of previous call
        uint256 liquidity = want.balanceOf(address(cToken));

        if (liquidity > 1) {
            uint256 toWithdraw = amount.sub(looseBalance);

            if (toWithdraw <= liquidity) {
                //we can take all
                cToken.redeemUnderlying(toWithdraw); //auTokens methods do not return an uint for the status
            } else {
                //take all we can
                cToken.redeemUnderlying(liquidity);
            }
        }
        if(!ignorePrinting) {
            _disposeOfComp();
        }
        looseBalance = want.balanceOf(address(this));
        want.safeTransfer(address(strategy), looseBalance);
        return looseBalance;
    }

    function _disposeOfComp() internal {
        uint256 _comp = IERC20(comp).balanceOf(address(this));

        if (_comp > minCompToSell) {
            address[] memory path = new address[](3);
            path[0] = comp;
            path[1] = weth;
            path[2] = address(want);

            IUniswapV2Router02(uniswapRouter).swapExactTokensForTokens(_comp, uint256(0), path, address(this), now);
        }
    }

    function deposit() external override management {
        uint256 balance = want.balanceOf(address(this));
        if(balance > 0)
            cToken.mint(balance); // auTokens .mint() method does not return a uint
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

    function setIgnorePrinting(bool _ignorePrinting) external management {
        ignorePrinting = _ignorePrinting;
    }

    function protectedTokens() internal view override returns (address[] memory) {
        address[] memory protected = new address[](3);
        protected[0] = address(want);
        protected[1] = address(cToken);
        protected[2] = comp;
        return protected;
    }
}