// SPDX-License-Identifier: agpl-3.0
pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

interface  ILiquidHundredChef {
    // using SafeMath for uint256;
    // using BoringMath128 for uint256;
    // using BoringERC20 for IERC20;
    // using SignedSafeMath for int256;

    /// @notice Info of each MCV2 user.
    /// `amount` LP token amount the user has provided.
    /// `rewardDebt` The amount of TOKEN entitled to the user.
    struct UserInfo {
        uint256 amount;
        int256 rewardDebt;
    }

    /// @notice Info of each MCV2 pool.
    /// `allocPoint` The amount of allocation points assigned to the pool.
    /// Also known as the amount of TOKEN to distribute per block.
    struct PoolInfo {
        uint256 accTokenPerShare;
        uint256 lastRewardTime;
        uint256 allocPoint;
    }

    /// @notice Address of the reward TOKEN contract.
    function TOKEN() external view returns (address);

    // @notice The migrator contract. It has a lot of power. Can only be set through governance (owner).
    function migrator() external view returns (address);

    /// @notice Info of each MCV2 pool.
    // PoolInfo[] public poolInfo;
    function poolInfo(uint256 _pid) external view returns (PoolInfo calldata);

    /// @notice Address of the LP token for each MCV2 pool.
    // IERC20[] public lpToken;
    function lpToken(uint256 _pid) external view returns (address);

    // /// @notice Address of each `ISecondRewarder` contract in MCV2.
    // ISecondRewarder[] public rewarder;
    // /// @notice Address of each `IStrategy`.
    // IStrategy[] public strategies;

    /// @notice Info of each user that stakes LP tokens.
    // mapping(uint256 => mapping(address => UserInfo)) public userInfo;
    function userInfo(uint256 _pid, address _user) external view returns (UserInfo calldata);

    function tokenPerSecond() external view returns (uint256);

    /// @dev Tokens added
    // mapping(address => bool) public addedTokens;

    /// @dev Total allocation points. Must be the sum of all allocation points in all pools.
    // uint256 public totalAllocPoint;

    // uint256 public tokenPerSecond;
    // uint256 public ACC_TOKEN_PRECISION;

    // uint256 public distributionPeriod;
    // uint256 public lastDistributedTime;

    // uint256 public overDistributed;

    // address public liHNDStrategy;
    function liHNDStrategy() external view returns (address);

    // string public __NAME__;

    /// @notice Returns the number of MCV2 pools.
    function poolLength() external view returns (uint256 pools);

    /// @notice Migrate LP token to another LP contract through the `migrator` contract.
    /// @param _pid The index of the pool. See `poolInfo`.
    function migrate(uint256 _pid) external;

    /// @notice View function to see pending TOKEN on frontend.
    /// @param _pid The index of the pool. See `poolInfo`.
    /// @param _user Address of user.
    /// @return pending TOKEN reward for a given user.
    function pendingToken(uint256 _pid, address _user)
        external
        view
        returns (uint256 pending);

    /// @notice Update reward variables for all pools. Be careful of gas spending!
    /// @param pids Pool IDs of all to be updated. Make sure to update all active pools.
    function massUpdatePools(uint256[] calldata pids) external;

    function massUpdateAllPools() external;

    /// @notice Update reward variables of the given pool.
    /// @param pid The index of the pool. See `poolInfo`.
    /// @return pool Returns the pool that was updated.
    function updatePool(uint256 pid) external returns (PoolInfo memory pool);

    /// @notice Deposit LP tokens to MCV2 for TOKEN allocation.
    /// @param pid The index of the pool. See `poolInfo`.
    /// @param amount LP token amount to deposit.
    /// @param to The receiver of `amount` deposit benefit.
    function deposit(
        uint256 pid,
        uint256 amount,
        address to
    ) external;


    /// @notice Withdraw LP tokens from MCV2.
    /// @param pid The index of the pool. See `poolInfo`.
    /// @param amount LP token amount to withdraw.
    /// @param to Receiver of the LP tokens.
    function withdraw(
        uint256 pid,
        uint256 amount,
        address to
    ) external;

    /// @notice Harvest proceeds for transaction sender to `to`.
    /// @param pid The index of the pool. See `poolInfo`.
    /// @param to Receiver of TOKEN rewards.
    function harvest(uint256 pid, address to) external;

    /// @notice Withdraw LP tokens from MCV2 and harvest proceeds for transaction sender to `to`.
    /// @param pid The index of the pool. See `poolInfo`.
    /// @param amount LP token amount to withdraw.
    /// @param to Receiver of the LP tokens and TOKEN rewards.
    function withdrawAndHarvest(
        uint256 pid,
        uint256 amount,
        address to
    ) external;

    /// @notice Withdraw without caring about rewards. EMERGENCY ONLY.
    /// @param pid The index of the pool. See `poolInfo`.
    /// @param to Receiver of the LP tokens.
    function emergencyWithdraw(uint256 pid, address to) external;
}