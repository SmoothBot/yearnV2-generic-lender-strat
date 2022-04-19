// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.6.12;

struct GenericLenderParameters { 
    //These parameters changes for every different chain
    uint256 _blocksPerYear;
    address _uniswapRouter;
    address _weth;
    //These parameters changes for every different protocol
    address _comp;
    string _name;
    //These parameters changes for every different token/strategy
    address _cToken;
    address _strategy;

}
