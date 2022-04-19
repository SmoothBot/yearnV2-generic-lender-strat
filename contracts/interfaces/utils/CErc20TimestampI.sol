// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.6.12;

interface CErc20TimestampI is CErc20IGeneric{
    function transfer(address dst, uint amount) external virtual returns (bool);
    function transferFrom(address src, address dst, uint amount) external virtual returns (bool);
    function approve(address spender, uint amount) external virtual returns (bool);
    function allowance(address owner, address spender) external virtual view returns (uint);
    function balanceOf(address owner) external virtual view returns (uint);
    function balanceOfUnderlying(address owner) external virtual returns (uint);
    function getAccountSnapshot(address account) external virtual view returns (uint, uint, uint);
    function borrowRatePerTimestamp() external virtual view returns (uint);
    function supplyRatePerTimestamp() external virtual view returns (uint);
    function totalBorrowsCurrent() external virtual returns (uint);
    function borrowBalanceCurrent(address account) external virtual returns (uint);
    function borrowBalanceStored(address account) public view virtual returns (uint);
    function exchangeRateCurrent() public virtual returns (uint);
    function exchangeRateStored() public view virtual returns (uint);
    function getBorrowDataOfAccount(address account) public view virtual returns (uint, uint);
    function getSupplyDataOfOneAccount(address account) public view virtual returns (uint, uint);
    function getSupplyDataOfTwoAccount(address account1, address account2) public view virtual returns (uint, uint, uint);
    function getCash() external virtual view returns (uint);
    function accrueInterest() public virtual;
    function seize(address liquidator, address borrower, uint seizeTokens) external virtual;
}