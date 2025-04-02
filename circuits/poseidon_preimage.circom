include "poseidon.circom";

template PoseidonPreimage() {
    signal input x;
    signal input expected;

    signal output isValid;

    component hasher = Poseidon(1);
    hasher.inputs[0] <== x;

    signal diff;
    diff <== hasher.out - expected;
    isValid <== 1 - diff * diff;
}

component main = PoseidonPreimage();
