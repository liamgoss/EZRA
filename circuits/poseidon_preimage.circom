include "poseidon.circom";

template PoseidonPreimage() {
    signal input x;
    signal input expected;

    component hasher = Poseidon(1);
    hasher.inputs[0] <== x;

    expected === hasher.out;
}

component main {public [expected]} = PoseidonPreimage();