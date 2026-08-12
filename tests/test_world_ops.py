"""Tests for the .world library, ops, and CLI."""

import copy
import json
from pathlib import Path

import pytest

from sids_3dx_utils import cli, ops
from sids_3dx_utils.world import (
    count_objects,
    iter_objects,
    load_world,
    new_world,
    save_world,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
ARIAL_WORLD = REPO_ROOT / "fonts" / "arial" / "arial.world"


def make_obj(name="Box", p=(0.0, 0.0, 0.0), r=(0.0, 0.0, 0.0),
             s=(1.0, 1.0, 1.0), c=(1.0, 1.0, 1.0)):
    return {"n": name, "p": list(p), "r": list(r), "s": list(s), "c": list(c)}


def make_world():
    return new_world(objects=[
        make_obj(p=(0, 0, 0), c=(1.0, 0.0, 0.0)),
        make_obj(p=(5, 0, 0), r=(0.0, 89.5, 0.0)),
        {"n": "group", "objects": [
            make_obj("Tube", p=(10, 1, 2), c=(1.0, 0.0, 0.0)),
            make_obj("Light", p=(10, 5, 2), c=(1.0, 0.0, 0.0)),
        ]},
    ])


# ---------------------------------------------------------------- world I/O

def test_round_trip(tmp_path):
    world = make_world()
    path = tmp_path / "w.world"
    save_world(world, path)
    again = load_world(path)
    assert again == world


def test_load_real_font_world():
    world = load_world(ARIAL_WORLD)
    assert count_objects(world) > 100
    names = {obj["n"] for obj in iter_objects(world)}
    assert "Box" in names


def test_iter_objects_descends_groups():
    world = make_world()
    assert count_objects(world) == 4
    with_groups = list(iter_objects(world, include_groups=True))
    assert sum(1 for o in with_groups if o["n"] == "group") == 1


# --------------------------------------------------------------------- move

def test_move_world_offsets_everything():
    world = make_world()
    moved = ops.move_world(world, (10.0, 0.0, -2.0))
    assert moved == 4
    first = world["objects"][0]
    assert first["p"] == [10.0, 0.0, -2.0]
    assert world["respawn"]["p"] == [10.0, 0.0, -2.0]


def test_move_with_bbox_only_hits_inside():
    world = make_world()
    box = ops.BoundingBox((-1, -1, -1), (1, 1, 1))
    moved = ops.move_world(world, (100.0, 0.0, 0.0), bbox=box)
    assert moved == 1
    assert world["objects"][0]["p"] == [100.0, 0.0, 0.0]
    assert world["objects"][1]["p"] == [5.0, 0.0, 0.0]
    # scoped moves leave respawn alone
    assert world["respawn"]["p"] == [0.0, 0.0, 0.0]


# -------------------------------------------------------------------- merge

def test_merge_adds_objects_and_leaves_source_alone():
    a = make_world()
    b = make_world()
    before = copy.deepcopy(b)
    added = ops.merge_worlds(a, b, offset=(50.0, 0.0, 0.0))
    assert added == 4
    assert count_objects(a) == 8
    assert b == before
    merged_positions = [o["p"][0] for o in iter_objects(a)]
    assert any(x >= 50.0 for x in merged_positions)


# ------------------------------------------------------------------- dedupe

def test_remove_duplicates_ignores_color():
    world = new_world(objects=[
        make_obj(c=(1.0, 0.0, 0.0)),
        make_obj(c=(0.0, 1.0, 0.0)),  # same placement, different color
        make_obj(p=(9, 9, 9)),
    ])
    removed = ops.remove_duplicates(world)
    assert removed == 1
    assert count_objects(world) == 2


def test_remove_duplicates_prunes_emptied_groups():
    world = new_world(objects=[
        make_obj(),
        {"n": "group", "objects": [make_obj()]},
    ])
    removed = ops.remove_duplicates(world)
    assert removed == 1
    assert world["objects"] == [make_obj()]


# ------------------------------------------------------------------ recolor

def test_replace_color_exact_and_tolerance():
    world = make_world()
    changed = ops.replace_color(world, (1.0, 0.0, 0.0), (0.0, 0.0, 1.0))
    assert changed == 3
    assert world["objects"][0]["c"] == [0.0, 0.0, 1.0]

    world2 = new_world(objects=[make_obj(c=(0.99, 0.01, 0.0))])
    assert ops.replace_color(world2, (1, 0, 0), (0, 1, 0)) == 0
    assert ops.replace_color(
        world2, (1, 0, 0), (0, 1, 0), tolerance=0.02
    ) == 1


def test_replace_color_light_filters():
    world = make_world()
    only = ops.replace_color(
        world, (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), lights=ops.LIGHTS_ONLY
    )
    assert only == 1
    skipped = ops.replace_color(
        world, (1.0, 0.0, 0.0), (0.5, 0.5, 0.5), lights=ops.LIGHTS_EXCLUDE
    )
    assert skipped == 2


# -------------------------------------------------------------- snap angles

def test_round_angles_snaps_within_tolerance():
    world = make_world()
    changed = ops.round_angles(world, step=90.0, tolerance=2.0)
    assert changed == 1
    assert world["objects"][1]["r"] == [0.0, 90.0, 0.0]


def test_round_angles_leaves_far_angles():
    world = new_world(objects=[make_obj(r=(45.0, 0.0, 0.0))])
    assert ops.round_angles(world, step=90.0, tolerance=2.0) == 0
    assert world["objects"][0]["r"] == [45.0, 0.0, 0.0]


# -------------------------------------------------------------------- scale

def test_scale_world():
    world = new_world(objects=[make_obj(p=(2.0, 4.0, 6.0))])
    ops.scale_world(world, 0.5)
    obj = world["objects"][0]
    assert obj["p"] == [1.0, 2.0, 3.0]
    assert obj["s"] == [0.5, 0.5, 0.5]


def test_scale_rejects_nonpositive():
    with pytest.raises(ValueError):
        ops.scale_world(new_world(), 0)


# -------------------------------------------------------------------- stats

def test_world_stats():
    stats = ops.world_stats(make_world())
    assert stats["objects"] == 4
    assert stats["types"]["Box"] == 2
    assert stats["unique_colors"] == 2
    assert stats["bounds"]["min"] == [0.0, 0.0, 0.0]
    assert stats["bounds"]["max"] == [10.0, 5.0, 2.0]


# ---------------------------------------------------------------------- CLI

def test_cli_info(tmp_path, capsys):
    path = tmp_path / "w.world"
    save_world(make_world(), path)
    assert cli.main(["info", str(path)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["objects"] == 4


def test_cli_move_and_dedupe(tmp_path, capsys):
    src = tmp_path / "in.world"
    dst = tmp_path / "out.world"
    save_world(make_world(), src)

    assert cli.main([
        "move", str(src), str(dst), "--offset", "1", "2", "3",
    ]) == 0
    moved = load_world(dst)
    assert moved["objects"][0]["p"] == [1.0, 2.0, 3.0]

    dup = new_world(objects=[make_obj(), make_obj()])
    save_world(dup, src)
    assert cli.main(["dedupe", str(src), str(dst)]) == 0
    assert count_objects(load_world(dst)) == 1


def test_cli_merge(tmp_path, capsys):
    a = tmp_path / "a.world"
    b = tmp_path / "b.world"
    out = tmp_path / "out.world"
    save_world(make_world(), a)
    save_world(make_world(), b)
    assert cli.main([
        "merge", str(a), str(b), str(out), "--offset", "100", "0", "0",
    ]) == 0
    assert count_objects(load_world(out)) == 8
