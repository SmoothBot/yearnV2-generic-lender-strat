// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.6.12;

import "../Compound/InterestRateModel.sol";
import "../Compound/ComptrollerI.sol";
/// @dev Original contracts here -> https://aurorascan.dev/address/0x4f0d864b1ABf4B701799a0b30b57A22dFEB5917b#code

/**
    @notice This is a parallel of CToken. 
    All the methods are identical, except for borrowRatePerTimestamp and supplyRatePerTimestamp
    This was AuTokenInterface 
*/
interface CTokenTimestampI {
    /*** Market Events ***/

    /**
     * @notice Event emitted when interest is accrued
     */
    event AccrueInterest(uint cashPrior, uint interestAccumulated, uint borrowIndex, uint totalBorrows);

    /**
     * @notice Event emitted when tokens are minted
     */
    event Mint(address minter, uint mintAmount, uint mintTokens);

    /**
     * @notice Event emitted when tokens are redeemed
     */
    event Redeem(address redeemer, uint redeemAmount, uint redeemTokens);

    /**
     * @notice Event emitted when underlying is borrowed
     */
    event Borrow(address borrower, uint borrowAmount, uint accountBorrows, uint totalBorrows);

    /**
     * @notice Event emitted when a borrow is repaid
     */
    event RepayBorrow(address payer, address borrower, uint repayAmount, uint accountBorrows, uint totalBorrows);

    /**
     * @notice Event emitted when a borrow is liquidated
     */
    event LiquidateBorrow(address liquidator, address borrower, uint repayAmount, address auTokenCollateral, uint seizeTokens);


    /*** Admin Events ***/

    /**
     * @notice Event emitted when pendingAdmin is changed
     */
    event NewPendingAdmin(address oldPendingAdmin, address newPendingAdmin);

    /**
     * @notice Event emitted when pendingAdmin is accepted, which means admin is updated
     */
    event NewAdmin(address oldAdmin, address newAdmin);

    /**
     * @notice Event emitted when comptroller is changed
     */
    event NewComptroller(ComptrollerI oldComptroller, ComptrollerI newComptroller);

    /**
     * @notice Event emitted when interestRateModel is changed
     */
    event NewMarketInterestRateModel(InterestRateModel oldInterestRateModel, InterestRateModel newInterestRateModel);

    /**
     * @notice Event emitted when the reserve factor is changed
     */
    event NewReserveFactor(uint oldReserveFactorMantissa, uint newReserveFactorMantissa);

    /**
     * @notice Event emitted when the protocol seize share is changed
     */
    event NewProtocolSeizeShare(uint oldProtocolSeizeShareMantissa, uint newProtocolSeizeShareMantissa);

    /**
     * @notice Event emitted when the reserves are added
     */
    event ReservesAdded(address benefactor, uint addAmount, uint newTotalReserves);

    /**
     * @notice Event emitted when the reserves are reduced
     */
    event ReservesReduced(address admin, uint reduceAmount, uint newTotalReserves);

    /**
     * @notice EIP20 Transfer event
     */
    event Transfer(address indexed from, address indexed to, uint amount);

    /**
     * @notice EIP20 Approval event
     */
    event Approval(address indexed owner, address indexed spender, uint amount);


    /*** User Interface ***/

    function transfer(address dst, uint amount) external returns (bool);

    function transferFrom(address src, address dst, uint amount) external returns (bool);
    
    function approve(address spender, uint amount) external returns (bool);
    
    function allowance(address owner, address spender) external view returns (uint256);
    
    function balanceOf(address owner) external view returns (uint256);
    
    function balanceOfUnderlying(address owner) external returns (uint);
    
    function getAccountSnapshot(address account) external view returns (uint, uint, uint); 
    
    function borrowRatePerTimestamp() external view returns (uint);
    
    function supplyRatePerTimestamp() external view returns (uint);
    
    function totalBorrowsCurrent() external returns (uint);
    
    function borrowBalanceCurrent(address account) external returns (uint);
    
    function borrowBalanceStored(address account) external view returns (uint);
    
    function exchangeRateCurrent() external returns (uint);
    
    function exchangeRateStored() external view returns (uint256);
    
    function getCash() external view returns (uint);
    
    function accrueInterest() external returns (uint256);
    
    function interestRateModel() external view returns (InterestRateModel);

    function totalReserves() external view returns (uint256);

    function reserveFactorMantissa() external view returns (uint256);

    function seize(address liquidator, address borrower, uint seizeTokens) external virtual;

    function totalBorrows() external view returns (uint256);

    function totalSupply() external view returns (uint256);

    // These methods are not present in CTokenI
    // function getBorrowDataOfAccount(address account) public view virtual returns (uint, uint);
    // function getSupplyDataOfOneAccount(address account) public view virtual returns (uint, uint);
    // function getSupplyDataOfTwoAccount(address account1, address account2) public view virtual returns (uint, uint, uint);

}

interface CErc20TimestampI is CTokenTimestampI {
    function mint(uint256 mintAmount) external;

    function redeem(uint256 redeemTokens) external;

    function comptroller() external view returns (address);

    function redeemUnderlying(uint256 redeemAmount) external;

    function borrow(uint256 borrowAmount) external;

    function repayBorrow(uint256 repayAmount) external;

    function repayBorrowBehalf(address borrower, uint256 repayAmount) external;

    function liquidateBorrow(
        address borrower,
        uint256 repayAmount,
        CTokenI cTokenCollateral
    ) external ;

    function underlying() external view returns (address);

}

