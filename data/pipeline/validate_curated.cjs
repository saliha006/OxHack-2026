// Validate concrete imported sets against the locally pinned Gen9 OU rules/learnsets.
const fs = require('node:fs');
const path = require('node:path');
const {TeamValidator} = require(path.join(path.resolve(process.argv[2]), 'dist/sim'));
const rows = JSON.parse(fs.readFileSync(0, 'utf8'));
const stats = ['hp','atk','def','spa','spd','spe'];
const results = rows.map(row => {
  const c = row.candidate;
  const set = {name: row.species, species: row.species, level: 100,
    moves: c.moves, ability: c.ability, item: c.item, nature: c.spread.nature,
    teraType: c.tera_type,
    evs: Object.fromEntries(stats.map((s,i) => [s,c.spread.evs[i]])),
    ivs: Object.fromEntries(stats.map((s,i) => [s,(c.ivs || [31,31,31,31,31,31])[i]]))};
  return {id: row.id, errors: new TeamValidator('gen9ou').validateTeam([set]) || []};
});
process.stdout.write(JSON.stringify(results)+'\n');
