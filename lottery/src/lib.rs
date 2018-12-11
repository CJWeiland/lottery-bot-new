#![feature(specialization)]

#[macro_use]
extern crate pyo3;
extern crate rand;

use rand::rngs::SmallRng;
use rand::prelude::*;
use pyo3::prelude::*;


fn gen_5(seed: u64) -> Vec<u8> {
    let mut r = SmallRng::seed_from_u64(seed);

    let mut v: Vec<u8> = vec![];

    for _ in 0..5 {
        let mut n: u8 = r.gen_range(1, 71);
        while v.contains(&n) {
            n = r.gen_range(1, 71);
        }
        v.push(n);
    }

    v.sort();
    v.push(r.gen_range(1, 26));

    v
}

#[pyfunction]
fn gen_numbers(seed: u64) -> PyResult<Vec<u8>> {
    Ok(gen_5(seed))
}

#[pyfunction]
fn matches(seed_1: u64, seed_2: u64) -> PyResult<(u8, bool)> {
    let s_1 = gen_5(seed_1);
    let s_2 = gen_5(seed_2);

    let mut matches = 0;
    for i in s_1.iter() {
        if s_2.contains(i) {
            matches += 1;
        }
    }

    let mut bonus = false;
    if s_1.last() == s_2.last() {
        matches -= 1;
        bonus = true;
    }

    return Ok((matches, bonus))
}

#[pymodinit]
fn lottery(py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_function!(gen_numbers))?;
    m.add_function(wrap_function!(matches))?;

    Ok(())
}
