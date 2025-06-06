export const description = `
Execution tests for the 'pack4xI8' builtin function

@const fn pack4xI8(e: vec4<i32>) -> u32
Pack the lower 8 bits of each component of e into a u32 value and drop all the unused bits.
Component e[i] of the input is mapped to bits (8 * i) through (8 * (i + 7)) of the result.
`;

import { makeTestGroup } from '../../../../../../common/framework/test_group.js';
import { AllFeaturesMaxLimitsGPUTest } from '../../../../../gpu_test.js';
import { u32, toVector, i32, Type } from '../../../../../util/conversion.js';
import { Case } from '../../case.js';
import { allInputSources, Config, run } from '../../expression.js';

import { builtin } from './builtin.js';

export const g = makeTestGroup(AllFeaturesMaxLimitsGPUTest);

g.test('basic')
  .specURL('https://www.w3.org/TR/WGSL/#pack4xI8-builtin')
  .desc(
    `
@const fn pack4xI8(e: vec4<i32>) -> u32
  `
  )
  .params(u => u.combine('inputSource', allInputSources))
  .fn(async t => {
    const cfg: Config = t.params;

    const pack4xI8 = (vals: readonly [number, number, number, number]) => {
      const result = new Uint32Array(1);
      for (let i = 0; i < 4; ++i) {
        result[0] |= (vals[i] & 0xff) << (i * 8);
      }
      return result[0];
    };

    const testInputs = [
      [0, 0, 0, 0],
      [1, 2, 3, 4],
      [-1, 2, 3, 4],
      [1, -2, 3, 4],
      [1, 2, -3, 4],
      [1, 2, 3, -4],
      [-1, -2, 3, 4],
      [-1, 2, -3, 4],
      [-1, 2, 3, -4],
      [1, -2, -3, 4],
      [1, -2, 3, -4],
      [1, 2, -3, -4],
      [-1, -2, -3, 4],
      [-1, -2, 3, -4],
      [-1, 2, -3, -4],
      [1, -2, -3, -4],
      [-1, -2, -3, -4],
      [127, 128, -128, -129],
      [128, 128, -128, -128],
      [32767, 32768, -32768, -32769],
    ] as const;

    const makeCase = (vals: readonly [number, number, number, number]): Case => {
      return { input: [toVector(vals, i32)], expected: u32(pack4xI8(vals)) };
    };
    const cases: Array<Case> = testInputs.flatMap(v => {
      return [makeCase(v)];
    });

    await run(t, builtin('pack4xI8'), [Type.vec4i], Type.u32, cfg, cases);
  });
