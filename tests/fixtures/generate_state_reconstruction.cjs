// Mechanics development fixture; no scoring teams or outcomes are selected here.
const fs = require('node:fs');
const path = require('node:path');
const {execFileSync} = require('node:child_process');
const root = path.resolve(__dirname, '../..');
const {Battle} = require(path.join(root, 'pokemon-showdown/dist/sim'));
const battle = new Battle({formatid: 'gen9customgame', seed: [1, 2, 3, 4]});
battle.setPlayer('p1', {name: 'A', team: [
  {species: 'Corviknight', ability: 'Pressure', moves: ['Protect', 'U-turn'], evs: {hp: 252}, nature: 'Serious'},
  {species: 'Kingambit', ability: 'Supreme Overlord', moves: ['Iron Head']},
]});
battle.setPlayer('p2', {name: 'B', team: [{species: 'Blissey', ability: 'Natural Cure', moves: ['Splash']}]});
const frames = [];
let previous = 0;
function snapshot(label) {
  const active = battle.sides[0].active[0];
  frames.push({label,
    protocol: battle.log.slice(previous).filter(line => !line.startsWith('|t:|')),
    request: JSON.parse(JSON.stringify(battle.sides[0].activeRequest)),
    expected: {
      active: active.species.id,
      protect_streak: active.volatiles.stall ? Math.round(Math.log(active.volatiles.stall.counter) / Math.log(3)) : 0,
      own_pp: Object.fromEntries(battle.sides[0].pokemon.map(mon => [mon.species.id,
        Object.fromEntries(mon.moveSlots.map(move => [move.id, move.pp]))])),
    },
  });
  previous = battle.log.length;
}
battle.makeChoices('team 12', 'team 1');
snapshot('initial');
battle.makeChoices('move protect', 'move splash');
snapshot('first protect success');
battle.makeChoices('move protect', 'move splash');
snapshot('second protect success');
battle.makeChoices('move uturn', 'move splash');
snapshot('living pivot continuation');
battle.makeChoices('switch 2', '');
snapshot('after pivot replacement and end of turn');
const fixture = {showdown_revision: execFileSync('git', ['rev-parse', 'HEAD'],
  {cwd: path.join(root, 'pokemon-showdown'), encoding: 'utf8'}).trim(),
  format: 'gen9customgame', seed: [1, 2, 3, 4],
  purpose: 'State mechanics only; custom game permits a short controlled roster. No strength or OU team-validation claim.',
  frames};
fs.writeFileSync(path.join(__dirname, 'state_reconstruction_showdown.json'), JSON.stringify(fixture, null, 2) + '\n');
