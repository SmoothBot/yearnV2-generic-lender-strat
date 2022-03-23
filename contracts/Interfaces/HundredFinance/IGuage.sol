// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

interface IGuage is IERC20 {
    function claimRewards(
        address[] memory holders,
        address[] memory cTokens,
        address[] memory rewards,
        bool borrowers,
        bool suppliers
    ) external;

    function rewardSupplySpeeds(address, address)
        external
        view
        returns (
            uint256,
            uint256,
            uint256
        );

    function rewardTokensMap(address) external view returns (bool);

    function deposit(uint256) external;

    function withdraw(uint256) external;

    function minter() external view returns (address);

    function controller() external view returns (address);

    function reward_policy_maker() external view returns (address);

    function working_supply() external view returns (uint256);

    function inflation_rate() external view returns (uint256);
}