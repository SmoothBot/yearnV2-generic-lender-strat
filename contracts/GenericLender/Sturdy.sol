// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/math/SafeMath.sol";
import "@openzeppelin/contracts/utils/Address.sol";
import "@openzeppelin/contracts/token/ERC20/SafeERC20.sol";

import "../Interfaces/UniswapInterfaces/IUniswapV2Router02.sol";
import "../Interfaces/Aave/IAToken.sol";
import "../Interfaces/Aave/IStakedAave.sol";
import "../Interfaces/Aave/ILendingPool.sol";
import "../Interfaces/Aave/IProtocolDataProvider.sol";
import "../Interfaces/Aave/IAaveIncentivesController.sol";
import "../Interfaces/Aave/IReserveInterestRateStrategy.sol";
import "../Interfaces/Sturdy/ILendingPoolAddressesProvider.sol";
import "../Libraries/Aave/DataTypes.sol";

import "./GenericLenderBase.sol";

// Contracts: https://github.com/sturdyfi/sturdy-contracts/blob/main/ftm-contracts.json
// Lending pools: https://ftmscan.com/address/0x06caE399575E3d20cD4B468c8Ef53fAdd2C6aEC8#code
// Docs: https://docs.sturdy.finance/overview/what-is-sturdy
// To find sTokens, use https://ftmscan.com/address/0xc06dc19a4efa1a832f4618ce383d8cb9c7f4d600#readContract getReserveTokensAddresses()
/// @title Sturdy finance lender, based on GenericAave lender
/// @author hero-borg
/// @notice Right now the lending is not incentivised, so I removed all the parts with the incentives
contract Sturdy is GenericLenderBase {
    using SafeERC20 for IERC20;
    using Address for address;
    using SafeMath for uint256;
   
    IProtocolDataProvider public constant protocolDataProvider = IProtocolDataProvider(address(0xC06Dc19a4efA1a832F4618Ce383d8cB9c7F4D600));
    IAToken public aToken;

    address public keep3r;

    address public constant WFTM = address(0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2);

    IUniswapV2Router02 public constant router =
        IUniswapV2Router02(address(0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D));

    uint256 constant internal SECONDS_IN_YEAR = 365 days;

    constructor(
        address _strategy,
        string memory name,
        IAToken _aToken,
        bool _isIncentivised
    ) public GenericLenderBase(_strategy, name) {
        _initialize(_aToken, _isIncentivised);
    }

    function initialize(IAToken _aToken) external {
        _initialize(_aToken, _isIncentivised);
    }

    function _initialize(IAToken _aToken) internal {
        require(address(aToken) == address(0), "Sturdy already initialized");
        aToken = _aToken;
        require(_lendingPool().getReserveData(address(want)).aTokenAddress == address(_aToken), "WRONG ATOKEN");
        IERC20(address(want)).safeApprove(address(_lendingPool()), -1);
    }

    function cloneSturdyLender(
        address _strategy,
        string memory _name,
        IAToken _aToken
    ) external returns (address newLender) {
        newLender = _clone(_strategy, _name);
        Sturdy(newLender).initialize(_aToken);
    }

    function setReferralCode(uint16 _customReferral) external management {
        require(_customReferral != 0, "!invalid referral code");
        customReferral = _customReferral;
    }

    function setKeep3r(address _keep3r) external management {
        keep3r = _keep3r;
    }

    function withdraw(uint256 amount) external override management returns (uint256) {
        return _withdraw(amount);
    }

    //emergency withdraw. sends balance plus amount to governance
    function emergencyWithdraw(uint256 amount) external override onlyGovernance {
        _lendingPool().withdraw(address(want), amount, address(this));

        want.safeTransfer(vault.governance(), want.balanceOf(address(this)));
    }

    function deposit() external override management {
        uint256 balance = want.balanceOf(address(this));
        _deposit(balance);
    }

    function withdrawAll() external override management returns (bool) {
        uint256 invested = _nav();
        uint256 returned = _withdraw(invested);
        return returned >= invested;
    }

    function nav() external view override returns (uint256) {
        return _nav();
    }

    function underlyingBalanceStored() public view returns (uint256 balance) {
        balance = aToken.balanceOf(address(this));
    }

    function apr() external view override returns (uint256) {
        return _apr();
    }

    function weightedApr() external view override returns (uint256) {
        return _apr().mul(_nav());
    }


    function hasAssets() external view override returns (bool) {
        return aToken.balanceOf(address(this)) > 0;
    }

    

    function _nav() internal view returns (uint256) {
        return want.balanceOf(address(this)).add(underlyingBalanceStored());
    }

    function _apr() internal view returns (uint256) {
        uint256 liquidityRate = uint256(_lendingPool().getReserveData(address(want)).currentLiquidityRate).div(1e9);// dividing by 1e9 to pass from ray to wad
        (uint256 availableLiquidity, uint256 totalStableDebt, uint256 totalVariableDebt, , , , , , , ) =
                    protocolDataProvider.getReserveData(address(want));
        uint256 incentivesRate = _incentivesRate(availableLiquidity.add(totalStableDebt).add(totalVariableDebt)); // total supplied liquidity in Aave v2
        return liquidityRate.add(incentivesRate);
    }

    //withdraw an amount including any want balance
    function _withdraw(uint256 amount) internal returns (uint256) {
        uint256 balanceUnderlying = aToken.balanceOf(address(this));
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
        uint256 liquidity = want.balanceOf(address(aToken));

        if (liquidity > 1) {
            uint256 toWithdraw = amount.sub(looseBalance);

            if (toWithdraw <= liquidity) {
                //we can take all
                _lendingPool().withdraw(address(want), toWithdraw, address(this));
            } else {
                //take all we can
                _lendingPool().withdraw(address(want), liquidity, address(this));
            }
        }
        looseBalance = want.balanceOf(address(this));
        want.safeTransfer(address(strategy), looseBalance);
        return looseBalance;
    }

    function _deposit(uint256 amount) internal {
        ILendingPool lp = _lendingPool();
        // NOTE: check if allowance is enough and acts accordingly
        // allowance might not be enough if
        //     i) initial allowance has been used (should take years)
        //     ii) lendingPool contract address has changed (Aave updated the contract address)
        if(want.allowance(address(this), address(lp)) < amount){
            IERC20(address(want)).safeApprove(address(lp), 0);
            IERC20(address(want)).safeApprove(address(lp), type(uint256).max);
        }

        uint16 referral;
        uint16 _customReferral = customReferral;
        if(_customReferral != 0) {
            referral = _customReferral;
        } else {
            referral = DEFAULT_REFERRAL;
        }

        lp.deposit(address(want), amount, address(this), referral);
    }

    function _lendingPool() internal view returns (ILendingPool lendingPool) {
        lendingPool = ILendingPool(protocolDataProvider.ADDRESSES_PROVIDER().getLendingPool());
    }

    function _checkCooldown() internal view returns (bool) {
        if(!isIncentivised) {
            return false;
        }

        uint256 cooldownStartTimestamp = IStakedAave(stkAave).stakersCooldowns(address(this));
        uint256 COOLDOWN_SECONDS = IStakedAave(stkAave).COOLDOWN_SECONDS();
        uint256 UNSTAKE_WINDOW = IStakedAave(stkAave).UNSTAKE_WINDOW();
        if(block.timestamp >= cooldownStartTimestamp.add(COOLDOWN_SECONDS)) {
            return block.timestamp.sub(cooldownStartTimestamp.add(COOLDOWN_SECONDS)) <= UNSTAKE_WINDOW || cooldownStartTimestamp == 0;
        } else {
            return false;
        }
    }


    function protectedTokens() internal view override returns (address[] memory) {
        address[] memory protected = new address[](2);
        protected[0] = address(want);
        protected[1] = address(aToken);
        return protected;
    }

    modifier keepers() {
        require(
            msg.sender == address(keep3r) || msg.sender == address(strategy) || msg.sender == vault.governance() || msg.sender == IBaseStrategy(strategy).management(),
            "!keepers"
        );
        _;
    }
}
