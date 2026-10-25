from data.pipeline.reveal_evidence import extract
import pytest

START='''|poke|p1|Gholdengo, L100|
|poke|p2|Dondozo, L100|
|start
|switch|p1a: Gold|Gholdengo, L100|100/100
|switch|p2a: Dozo|Dondozo, L100|100/100
|turn|1
'''


def test_records_observed_facts_once_and_before_reveal():
    log=START+'''|move|p2a: Dozo|Wave Crash|p1a: Gold
|-damage|p1a: Gold|80/100
|-heal|p2a: Dozo|100/100|[from] item: Leftovers
|turn|2
|move|p2a: Dozo|Wave Crash|p1a: Gold
|-terastallize|p2a: Dozo|Dragon
'''
    rows=list(extract(log,'battle',include_state=True))
    moves=[r for r in rows if r['field']=='move' and r['value']=='wavecrash']
    assert len(moves)==1 and moves[0]['turn']==1
    assert 'wavecrash' not in moves[0]['before']['sides']['p2']['pokemon'][0]['revealed_moves']
    assert any(r['field']=='item' and r['value']=='leftovers' and r['native_set_evidence'] for r in rows)
    assert any(r['field']=='tera_type' and r['value']=='dragon' for r in rows)
    assert not any(r['field'] in ('evs','ivs','nature') for r in rows)


def test_consumed_item_preserves_identity_and_current_empty_separately():
    rows=list(extract(START+'|-enditem|p2a: Dozo|Sitrus Berry|[eat]\n','battle'))
    item=next(r for r in rows if r['field']=='item')
    assert item['value']=='sitrusberry' and item['scope']=='held_before_loss' and item['native_set_evidence']
    assert any(r['field']=='current_item' and r['value']=='' and not r['native_set_evidence'] for r in rows)


def test_trick_and_called_moves_are_not_original_set_labels():
    log=START+'''|move|p1a: Gold|Trick|p2a: Dozo
|-item|p2a: Dozo|Choice Scarf|[from] move: Trick
|move|p2a: Dozo|Sleep Talk|p1a: Gold
|move|p2a: Dozo|Surf|p1a: Gold|[from] move: Sleep Talk
'''
    rows=list(extract(log,'battle'))
    assert not any(r['field']=='move' and r['value']=='surf' for r in rows)
    assert not next(r for r in rows if r['value']=='choicescarf')['native_set_evidence']


def test_transformed_and_illusion_side_evidence_is_censored():
    rows=list(extract(START+'|-transform|p2a: Dozo|p1a: Gold\n|move|p2a: Dozo|Shadow Ball|p1a: Gold\n','battle'))
    assert not next(r for r in rows if r['value']=='shadowball')['native_set_evidence']
    log=START.replace('|poke|p2|Dondozo, L100|','|poke|p2|Zoroark-Hisui, L100|')+'|move|p2a: Dozo|Surf|p1a: Gold\n'
    assert not next(r for r in extract(log,'battle') if r['field']=='move')['native_set_evidence']


def test_repeated_current_item_changes_keep_their_timing():
    log=START+'''|-enditem|p2a: Dozo|Sitrus Berry|[eat]
|turn|2
|-item|p2a: Dozo|Sitrus Berry|[from] move: Recycle
|turn|3
|-enditem|p2a: Dozo|Sitrus Berry|[eat]
'''
    rows=list(extract(log,'fixture'))
    assert [r['turn'] for r in rows if r['field']=='current_item']==[1,3]
    assert sum(r['native_set_evidence'] and r['field']=='item' for r in rows)==1


def test_mimic_is_native_but_subsequent_copied_slot_is_not_a_label():
    log=START+'|move|p2a: Dozo|Mimic|p1a: Gold\n|turn|2\n|move|p2a: Dozo|Shadow Ball|p1a: Gold\n'
    rows=list(extract(log,'fixture'))
    assert next(r for r in rows if r['value']=='mimic')['native_set_evidence']
    copied=next(r for r in rows if r['value']=='shadowball')
    assert not copied['native_set_evidence'] and copied['exclusion_reason']=='move_slot_may_have_been_copied'


def test_transformed_history_stays_censored_after_switch():
    log=START+'''|-transform|p2a: Dozo|p1a: Gold
|move|p2a: Dozo|Shadow Ball|p1a: Gold
|switch|p2a: Dozo|Dondozo, L100|100/100
|-item|p2a: Dozo|Leftovers
'''
    rows=list(extract(log,'fixture'))
    assert not next(r for r in rows if r['field']=='item')['native_set_evidence']


def test_export_does_not_delete_another_exports_partial_file(tmp_path):
    from data.pipeline.reveal_evidence import export_jsonl
    source=tmp_path/'source.jsonl';source.write_text('')
    output=tmp_path/'out.jsonl';part=tmp_path/'out.jsonl.part'
    part.write_text('another active export')
    with pytest.raises(FileExistsError): export_jsonl(source,output)
    assert part.read_text()=='another active export'
    assert not output.exists()
