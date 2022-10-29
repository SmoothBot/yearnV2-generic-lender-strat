// SPDX-License-Identifier: GPL-3.0
pragma solidity >=0.6.0 <0.7.0;

interface IWavax {
    function deposit() external payable;

    function withdraw(uint256 wad) external;

    function approve(address guy, uint256 wad) external returns (bool);
}
