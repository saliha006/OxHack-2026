/* Validate the locked author-sourced pool without editing any team or tuning settings. */
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const assert = require('assert/strict');
const {execFileSync} = require('child_process');
const root = path.resolve(__dirname, '..');
const {Teams} = require(path.join(root, 'pokemon-showdown/dist/sim/teams.js'));
const {TeamValidator} = require(path.join(root, 'pokemon-showdown/dist/sim/team-validator.js'));
const manifest = JSON.parse(fs.readFileSync(path.join(__dirname, 'mcts-heldout-provenance.json'), 'utf8'));
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
function canonical(team) {
  return JSON.stringify(team.map(s => ({
    species:s.species, item:s.item || '', ability:s.ability || '', nature:s.nature || '',
    evs:s.evs, ivs:s.ivs, moves:[...s.moves].sort(), teraType:s.teraType,
    level:s.level || 100, gender:s.gender || '', happiness:s.happiness ?? 255, shiny:!!s.shiny,
  })).sort((a, b) => a.species.localeCompare(b.species)));
}
const standin = fs.readdirSync(path.join(root, 'bot/teams/standin')).filter(f => f.endsWith('.txt')).map(file => {
  const bytes = fs.readFileSync(path.join(root, 'bot/teams/standin', file));
  return {file, sha256:sha(bytes), canonical_sha256:sha(canonical(Teams.import(bytes.toString('utf8'))))};
});
const results = [];
for (const source of manifest.teams) {
  const bytes = fs.readFileSync(path.join(root, source.file));
  assert.equal(sha(bytes), source.sha256, `${source.file}: changed since lock`);
  const team = Teams.import(bytes.toString('utf8'));
  assert.equal(team.length, 6);
  const canonicalHash = sha(canonical(team));
  assert.equal(canonicalHash, source.canonical_sets_sha256);
  const duplicates = standin.filter(s => s.sha256 === sha(bytes) || s.canonical_sha256 === canonicalHash);
  assert.equal(duplicates.length, 0, `${source.file}: overlaps standin`);
  const problems = TeamValidator.get(manifest.format).validateTeam(structuredClone(team));
  assert.equal(problems, null, `${source.file}: ${JSON.stringify(problems)}`);
  results.push({file:source.file, sha256:sha(bytes), pokemon:team.length, validator_problems:problems,
                standin_duplicates:duplicates});
}
console.log(JSON.stringify({
  format:manifest.format,
  validator_commit:execFileSync('git', ['-C', path.join(root, 'pokemon-showdown'), 'rev-parse', 'HEAD'], {encoding:'utf8'}).trim(),
  original_validator_commit:manifest.validator.commit,
  locked_at_utc:manifest.locked_at_utc,
  teams:results,
}, null, 2));
