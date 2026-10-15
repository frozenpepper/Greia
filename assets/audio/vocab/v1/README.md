# Shared vocabulary audio bank (v1)

Platform-owned, approved pedagogical noun clips shared by every Activity that
names a picture (Wonder Match, and any future matching/naming game). Activities
must resolve these through `greia_platform.localization.shared_vocab_audio_path`
(or `LocalizedResources.vocab_audio_path`) and must **never copy noun clips into
their own packages** (installed-disk budget). This mirrors the shared character
voice library (`../../characters/shared/v0.2/`).

## Layout and ids

    assets/audio/vocab/v1/<locale>/<noun_id>.wav
    assets/audio/vocab/v1/<locale>/<noun_id>.wav.receipt.json

* `<locale>` is the base language (`en`, `it`; `es`/`fr` stay staged).
* `<noun_id>` is the language-neutral concept id: lower-case `[a-z0-9_]`,
  equal to the final segment of the picture's semantic id
  (`prop.vocab.apple` / `prop.food.apple` -> `apple`; `creature.marine.dolphin`
  -> `dolphin`). The Italian clip for `apple` is therefore `it/apple.wav`
  (spoken "mela"); the id never changes per language.
* Fallback: requested locale chain -> base language -> English -> silence.
  A concept with no clip in a language falls back to English or stays silent.
* Receipts are the owner-approved generation receipts, moved unchanged. Their
  `output.path` still names the original Activity location (provenance).

To add a noun: add the approved clip + receipt here (never re-encode), add a row
below. Never edit or rename originals that remain in other Activities.

## Provenance (copied byte-identically from approved Activity clips)

| locale | noun_id | original clip | sha256 |
|---|---|---|---|
| en | apple | `activities/foresta_parole/assets/audio/en/apple.wav` | `81a6bfb7835a49251636dd21537b79fe128af27f1ed6bc34d8da4c20c9efc087` |
| en | boat | `activities/festa_delle_rime/assets/audio/en/boat.wav` | `8cee887f29f45ac25e84d4358cd4e4734442a4625d344bde24ab88fb02256454` |
| en | cake | `activities/festa_delle_rime/assets/audio/en/cake.wav` | `54581cb65af41ec6209418009489d19a198d567f8cd3bef38d11cdeb31e8e526` |
| en | car | `activities/festa_delle_rime/assets/audio/en/car.wav` | `64ea9c831969679b640d70e0761aca183b0d53c4d344408233cfffd6475d7877` |
| en | cat | `activities/festa_delle_rime/assets/audio/en/cat.wav` | `156d1a7f07fa7b7cdb51ad1aa0d191d60e5636d39cfb628800658f03a37a0c84` |
| en | dolphin | `activities/foresta_parole/assets/audio/en/dolphin.wav` | `97c69beed37ea66ae7cc89596d8ea301ae8ad3a47f620ef52b43a336c4a58023` |
| en | elephant | `activities/foresta_parole/assets/audio/en/elephant.wav` | `2817d297ab53e57fdde9f50ec6b7b022780ea177ea095b27eab7e5b5772173ec` |
| en | fish | `activities/festa_delle_rime/assets/audio/en/fish.wav` | `8b89fc3f4f059e1ee942c40fff267d0282e3d11c566e645314c117a06ba19234` |
| en | flower | `activities/foresta_parole/assets/audio/en/flower.wav` | `1a294c04737fe844411f055ed3a0d79f685aeb59e134da37500635beb5517247` |
| en | frog | `activities/festa_delle_rime/assets/audio/en/frog.wav` | `9ee8fa7ac3832da8cc87e926577819e0f2807aa86b93434d566686a3ecd42aba` |
| en | leaf | `activities/festa_delle_rime/assets/audio/en/leaf.wav` | `00155ae9c85b720649841bca0b2f3a07623bab5329ddeae411f29833915074ef` |
| en | lion | `activities/foresta_parole/assets/audio/en/lion.wav` | `aed8ec0894cd57d8f4442234257d3b6419fec8cc996fd49c0e4345959f135079` |
| en | moon | `activities/festa_delle_rime/assets/audio/en/moon.wav` | `cbe5ce5d6f38191f0cecf47ba85540f39fe26162940d741c3f252248e9daff1d` |
| en | mouse | `activities/festa_delle_rime/assets/audio/en/mouse.wav` | `a15c0c3a3f380e4d989668987bc4fa1563cd81da47f19fa6303a8ac6b1437285` |
| en | pear | `activities/festa_delle_rime/assets/audio/en/pear.wav` | `c582c9b8a909b38a154f7fa591d5c54f0f77466f6cea8c95d2067254ced9c6f0` |
| en | penguin | `activities/foresta_parole/assets/audio/en/penguin.wav` | `dae2d6bb58c0b24f72f10c302673911a387bb593fca5748e03858451999646b1` |
| en | pig | `activities/festa_delle_rime/assets/audio/en/pig.wav` | `c71e099f4df99d79139abe04acb8acd1f0e7d3bf2dd422d6420db77456ff0f51` |
| en | sun | `activities/festa_delle_rime/assets/audio/en/sun.wav` | `e6ee608c5cd8929514ef02ae9216cb4b0e82ec0a1df2e46470e4df19031adc6e` |
| en | turtle | `activities/festa_delle_rime/assets/audio/en/turtle.wav` | `e57bb76e38521483a017d12a43c921ff3fe85cf4c18a6c6b6cf25ed3ecd85a76` |
| en | pizza | `activities/sillabe_magiche/assets/audio/en/word_pizza.wav` | `b59745d1431c625e4f2e7c89a299b4eb058097afac81f6a0d2f4296164c51e5f` |
| en | rocket | `activities/sillabe_magiche/assets/audio/en/word_rocket.wav` | `2979bb5eac2fce68de81ece574e532b52353eb48088279c4c38dda3b875af692` |
| it | boat | `activities/foresta_parole/assets/audio/it/barca.wav` | `0b83783fd35042a1fa354545377fce1f6767e719829eddf853755f45ff641364` |
| it | dog | `activities/foresta_parole/assets/audio/it/cane.wav` | `8ae9ddc7eb0a38c3ef051741e7c04e95d71e1b4fa0e63bfd26f4915e6e11ef00` |
| it | dolphin | `activities/foresta_parole/assets/audio/it/delfino.wav` | `6186fc1119b2f4fdb5f5a3f8f7557abcb576429aa903a3658dc07c954c57fa13` |
| it | elephant | `activities/foresta_parole/assets/audio/it/elefante.wav` | `beec1c985696779bd096affe400c288689142b94bd993cb79ad24f304a75697f` |
| it | flower | `activities/festa_delle_rime/assets/audio/it/fiore.wav` | `09a58f17186503d8850d91cff263fdfea6f78fc84c40ea27a06ac622ce71e4be` |
| it | leaf | `activities/festa_delle_rime/assets/audio/it/foglia.wav` | `269422f8c557a2ac69ea16b7902cf137daccac0861e392b9245bba6f50313714` |
| it | cat | `activities/festa_delle_rime/assets/audio/it/gatto.wav` | `780b18949449bc6e058fdfac0744e814c9664e0f23208ca031a9f7aeb6d3a098` |
| it | moon | `activities/festa_delle_rime/assets/audio/it/luna.wav` | `6e980afe36a24c6d1b6eae3f92eda646b9e4d43df296f7e55eafe67f3a18eecc` |
| it | apple | `activities/festa_delle_rime/assets/audio/it/mela.wav` | `fbd2377f849ec41ad4c91c544eb792a4a8e3e527a4309c20fa79d961e67bea4a` |
| it | pear | `activities/festa_delle_rime/assets/audio/it/pera.wav` | `82549207f9dc8611585e6b924f2076aac781708072db6f6a07ddd937dc49887e` |
| it | fish | `activities/foresta_parole/assets/audio/it/pesce.wav` | `5affad5b3d6baf70c808170b6882aee9e8532213412f24c333897a9b080bb558` |
| it | frog | `activities/foresta_parole/assets/audio/it/rana.wav` | `981050d350bb649b3c6c63cd64190570ebba0f49ff3ea3b2c5079a6ea2d6e5ce` |
| it | sun | `activities/foresta_parole/assets/audio/it/sole.wav` | `2d4dc7440b0cfb4f8b4ddac7a432ad7607a786bbb98228d876721cd85bd7b0a6` |
| it | mouse | `activities/festa_delle_rime/assets/audio/it/topo.wav` | `5bfeecfbfb18ffa9592132a338b5e97051efd82f53f48e0e7fcda66c59215232` |
| it | cake | `activities/festa_delle_rime/assets/audio/it/torta.wav` | `92571773688ca3718e48a73780d7a85be496967af195b1778b8cc2e9d42b93d2` |
| it | grapes | `activities/foresta_parole/assets/audio/it/uva.wav` | `eb68e4e5946d7973df853aaa441a344dc79dc64ae6c3b4eee3f4d1c40a9465eb` |
| it | pizza | `activities/sillabe_magiche/assets/audio/it/word_pizza.wav` | `670da1bdf92fcfd997649ad6b681dcb66d09881f3b25a278f37a15b4b4c8fdba` |
