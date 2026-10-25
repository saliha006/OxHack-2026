// The coordinator knows teams; each player's stream exposes only its own private requests.
const readline = require('node:readline');
const path = require('node:path');
const simulatorRoot = path.resolve(process.argv[2]);
const {BattleStream, getPlayerStreams, Teams, TeamValidator} = require(path.join(simulatorRoot, 'dist/sim'));
const send = value => process.stdout.write(JSON.stringify(value) + '\n');
let streams, battleStream;
const input = readline.createInterface({input: process.stdin});
input.on('line', async line => {
  try {
    const command = JSON.parse(line);
    if (command.op === 'validate') {
      const results = command.teams.map(team => {
        const sets = Teams.import(team);
        return {errors: new TeamValidator('gen9ou').validateTeam(sets), packed: Teams.pack(sets)};
      });
      send({kind:'validated', results});
    } else if (command.op === 'start') {
      battleStream = new BattleStream({keepAlive:false});
      streams = getPlayerStreams(battleStream);
      const listeners = ['p1','p2','omniscient'].map(async side => {
        for await (const chunk of streams[side]) send({kind:'protocol', side, text:chunk});
      });
      Promise.all(listeners).then(() => send({kind:'end', winner:battleStream.battle.winner,
        turns:battleStream.battle.turn, seed:battleStream.battle.prngSeed})).catch(error => send({kind:'error', error:String(error)}));
      await streams.omniscient.write('>start ' + JSON.stringify({formatid:'gen9ou', seed:command.seed}) + '\n' +
        '>player p1 ' + JSON.stringify({name:'p1', team:command.teams.p1}) + '\n' +
        '>player p2 ' + JSON.stringify({name:'p2', team:command.teams.p2}));
    } else if (command.op === 'choose') {
      await streams[command.side].write(command.choice);
    } else if (command.op === 'tie') {
      await streams.omniscient.write('>forcetie');
    }
  } catch(error) { send({kind:'error', error:String(error), stack:error.stack}); }
});
