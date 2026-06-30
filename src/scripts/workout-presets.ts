// Fixed training routines, rendered in this order on the generator page.
// ids are record ids in fitness-exercises.json; the .test.mjs verifies they resolve.
export const PRESETS: { name: string; ids: string[] }[] = [
  { name: 'Upper Body A', ids: ['1350', '0577', '0579', '0603', '0602', '0584'] },
  { name: 'Lower Body A', ids: ['2138', '2287', '0585', '0599', '0739'] },
  { name: 'Upper Body B', ids: ['0314', '1350', '0579', '0603', '0577', '0596', '0584', '0607'] },
];
