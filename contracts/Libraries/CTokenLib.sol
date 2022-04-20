// SPDX-License-Identifier: agpl-3.0
pragma solidity 0.6.12;

import "../Interfaces/Compound/CErc20I.sol";
import "../Interfaces/utils/CErc20TimestampI.sol";
library CTokenLib {
    function getBorrowRate(address cTokenAddress, bool usesBlocks) public view returns (uint256) {
        return (usesBlocks)?CErc20I(cTokenAddress).borrowRatePerBlock():CErc20TimestampI(cTokenAddress).borrowRatePerTimestamp();
    }

    function getSupplyRate(address cTokenAddress, bool usesBlocks) public view returns (uint256) {
        return (usesBlocks)?CErc20I(cTokenAddress).supplyRatePerBlock():CErc20TimestampI(cTokenAddress).supplyRatePerTimestamp();
    }
}