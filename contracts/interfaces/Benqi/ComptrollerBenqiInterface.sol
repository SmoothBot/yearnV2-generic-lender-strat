// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.6.12;

interface ComptrollerBenqiInterface {
    function claimReward(uint8 rewardType, address payable holder) external;
}
