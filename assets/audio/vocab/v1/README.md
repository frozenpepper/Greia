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

* `<locale>` is the base language (`en`, `it`, `es`, `fr` — the four released languages).
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

## 2026-10-17 additions (generated, owner pre-approved)

Recorded with the local Voice Studio (`tools/greia_voice.py`, `pedagogical` speaker: macOS Samantha/Alice/Mónica/Thomas, the same voices as the approved clips above) after the owner approved all missing lines. Words come from the Activity bundles (Wonder Match `item.*`, Hide and Seek `animal.*`, My Puppy `name.*`) or the request list `docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/VOICE_LINES_REQUESTED_2026-10-16.md` (colours `colour_*`, positions `pos_*`, shapes `shape_*`, nouns). Receipts sit next to each clip.

| locale | noun_id | spoken text | sha256 |
|---|---|---|---|
| en | acorn | Acorn | `63878c0d8a542e2f6f565ea18865cb654d213fc98134c25f2d4bbaa7dfcbe9ee` |
| en | banana | Banana | `08ebf603d8ad449871cada50c3f8842fca0e249b4ebf9eb03dded53ab9102f9f` |
| en | bandage | Bandage | `aea954ce55c8687a8ba37082b4cb43424b97471a3e82e7c5df84d90d6175c5f0` |
| en | bean | Bean | `015c28bf19e8c7823b1c897a11868f4f74b15328defb42d017b601570ff6ef19` |
| en | bear | Bear | `e0a2fadb28598b0183c8c9fcb10d274073f3862aa2776b976904236c990ccdde` |
| en | bells | Bells | `3ca39b6dcda3922013a3223cb84d177e675366609fa5102447050abecd70fdbf` |
| en | bicycle | Bicycle | `fabf910e25ead12503f3e4ae55e5e362f301cdc5799c237ee0993db410696746` |
| en | blueberry | Blueberry | `3fec8a55556fedebeef7b93a98491e59d7a95dec765c7d91c72066a07ca863b4` |
| en | bus | Bus | `df942836f15b31cbec8e2c98ce7826128a1c215122a3ccb7cc019953aaed0e5d` |
| en | butterfly | Butterfly | `978f921065f607c5e978caefd4983b67b9b7454543a0528175a78818458cd71f` |
| en | carrot | Carrot | `550b3d2bdab1843e6629c000b688b418f96fb8b787e1a8b779317fb1049917da` |
| en | chair | Chair | `7bb7ecc332f6d47e11827eca01d6c3f2e203bd0787975bb0a7f43954018c587f` |
| en | cherry | Cherry | `633d48a5ff99613b20090c0424b7e633d0d231eac00c9ac0795819ebba56c011` |
| en | chocolate | Chocolate | `e785a7a64bf922368b51c6cb2b5e4faeef65c49ce50bc46a2c8ee37260dfbe8e` |
| en | colour_black | Black | `c2db9371d13e6fba618825bc22982caef4582176c2b4253e22b2e2e6a0a97ff4` |
| en | colour_blue | Blue | `7b45f9324f1890fa261d0b3425b679ad882671b52591c8d8954f7d2d52813d73` |
| en | colour_brown | Brown | `250a8ec6f161a0b112932c41493cf3a8432fa829c3c0a8ea5949563861ebd9bf` |
| en | colour_green | Green | `b12070544e13b4cb12c97ecba84db53b822f2261de4f5b80712cce12a755385b` |
| en | colour_orange | Orange | `590d0d1feb7796400db753f06f2adb5b629d7743d09f389c72d88c59e5086190` |
| en | colour_pink | Pink | `429dedf3a3b52585614f2a7017b5dcd29e2ed286446c5e50bd42bfd5b0ffd5c9` |
| en | colour_purple | Purple | `62d14be8ff41857cc493b492346a0c4114f42db629041a5f7535031221fec138` |
| en | colour_red | Red | `ac70523e9e85c2a2310ce06336cd99c1ef8947cf5521a5c261323c600b1d7706` |
| en | colour_white | White | `dde05c9da8d52b46ae97c7781b5e6330427790880a8a75980d1c8bd6a9b9537c` |
| en | colour_yellow | Yellow | `859018ddd89b85454e1e1d877f9f5ead094f62cd72c97b2c2077d5a720c3d058` |
| en | cookie | Cookie | `4f2ca0293327b2f9e81adb1d44d11c7f7b8d69d910e819b40a06a3abd4430521` |
| en | crab | Crab | `b3613bbef9e54743b9d1f80bc0ebce16b0b94a8f6ca823a168a7a7756a9f1611` |
| en | crown | Crown | `e91e13fc9bbd3e22a00e2c558fdc94108222e6785851d4a86346ca6524210e64` |
| en | deer | Deer | `870202fc2f0fa834fae85830894ace5cb0703035c4afe20cb87b5eeb1e56290b` |
| en | dog | Dog | `b38b41b61fefba2af50c7f7e1fc0f445d1d9ed9bb8b17c3844bfdc7f9644d914` |
| en | drum | Drum | `b87c320f23f0eca25d502b9d7807ae72232d26cab0503af0d830445198cb016a` |
| en | duck | Duck | `232360500aa78dccfa2c699d74aa546ca159f14681b4b1668fd31d1c76a15c83` |
| en | grapes | Grapes | `3f7fc9cf2638be72ba79c52b01a01936f2b755b6fc1be2ddf76aa4378ee7fb04` |
| en | guinea_pig | Guinea pig | `6338880925f3b5c30e5d29c75fbe46d6f18341ec0dbc654ea2afd6366357cd68` |
| en | hedgehog | Hedgehog | `4da95812fa9bcedb6c44f7790e99a7dad586ceacca19b8687d0ab011bdfda23b` |
| en | house | House | `952b8c078562d282d0b9e33b675b4c5643005575045e671e348ba267b74c3239` |
| en | ice_cream | Ice cream | `4c97ddc97d81ab95b0ea1f46f013aafc3708a3ae7265d4e17dd2d22cb82b9a5d` |
| en | igloo | Igloo | `3f5e58737c4ab1d7cf3c362261cf6aa8be941df141c159d94f46499fef67d082` |
| en | jellyfish | Jellyfish | `77482aa8e90845c452baabe53200464ed178f7a74494ccf21895fb547ca60a6c` |
| en | keyboard | Keyboard | `614d9d5e461b1ffb67d086421168a3a3ceccb9a377de86c9ce0c692f295ed2bd` |
| en | kite | Kite | `d37ca237fca53b27f22c1b87b2a5955c40fcf411fa87259b135fa38996bb2074` |
| en | kitten | Kitten | `6375f75664de69b869deceee5831598709912656715c89e1890afc1dfac99206` |
| en | lighthouse | Lighthouse | `e24618fd152024c07b44dfbdaa111909f2ccccf72e17e3494a794824bcf4a900` |
| en | maracas | Maracas | `400da5cbc419c6d6e0b0255c4eed1879db7b796374c07e5c5582a4d97c54c647` |
| en | medicine | Medicine | `f5acf8c883e9b8cb6ea4315943f06cf998dc075fbe622a969892eb4f519aa1e0` |
| en | mushroom | Mushroom | `6a4a37ac588ebe61a7cf57f6b67166272a7db6a8863941a682c687c3cc157d36` |
| en | mushrooms | Mushrooms | `3353a0d14ba5517336e57e4018cf122d934493c540a912d08bdf287d7c549850` |
| en | octopus | Octopus | `f14adb2566d522a6749c82a4633e0d6b1add6f1d1a003bd64f2683c5a3e3a52e` |
| en | plane | Plane | `54bdbfd9be58c3a5ed7392deaa74a3b1f4c944001fe2286e88872fb3d14843e1` |
| en | pos_behind | Behind | `78c0762cb1c9edfaaf101da9bdd08e4124cc6ce20a605384a2dd29e13b63d59c` |
| en | pos_down | Down | `9bbdb1e817553a14936ef9fefb6d13790041b2536244a2e806f25aa0837823ef` |
| en | pos_in | In | `ffd284b3c7292fd946c6b13b965740747a97c76c2629fb76f1e210ba1da3750b` |
| en | pos_in_front | In front of | `10b9a4402f41cc98e4aa0ca2df43a19139a8087b0e0d39f92317b0b8251c0e49` |
| en | pos_left | Left | `0fd2796538c56ff23774b6adc408dcbf13fc150bc3205da17ffb3817eddf2dd5` |
| en | pos_next_to | Next to | `61a4cf2c60c8e1086f63ec27ac451f3d85a6e0626ab014f876c31762489af399` |
| en | pos_on | On | `de307757e02e85a8376d15b06bdb6e12717c8424189665aff14ba183522d4723` |
| en | pos_right | Right | `8de245e2b6573af80d083cda0ad2eb197696312a81700de71ddeaddac654c7a0` |
| en | pos_under | Under | `a5667d78f1fdf6e95a53ad1d88d13d000bd08cfb59a289c36b3c3218ed2cdbbb` |
| en | pos_up | Up | `92d3f50a7d7fc17ab30bad9ad9921b8c14df0c5de66009053d43da74d4d8e7f0` |
| en | pos_where_is | Where is the…? | `106cca95f4db4ae00f3c884b5364a4baa3919e3ec5d1d9d8127dd6d29a2edf54` |
| en | pufferfish | Pufferfish | `c0eec24553596004cd8de6577068ee61816bc0a98b54284bdc86f7912bd46bee` |
| en | pumpkin | Pumpkin | `1deaa2ae2c2602c1b41f6abbae52abf61372b5e3300b5d3a1353ee8a6996093b` |
| en | puppy | Puppy | `3e17c9a9c7e49373afe0ad4ee3a365e96d11622ddb29078be7f73ada6ab7e9b0` |
| en | rain | Rain | `1de9494c68247abe2b238187ca430176d8decbef1a3e948e4e6dfd437e15488b` |
| en | rainbow | Rainbow | `4882dab2e825b0d1cc9df82529acfa1542ab0e8563d1fce36d5287a03a516144` |
| en | scarf | Scarf | `a589bd1f963adcb2846cb99a40a2165e865204ab0d58ac19fc79735a8b878871` |
| en | seahorse | Seahorse | `63a96dc251e076a61e6c27dcef3feb8f5ff6b73696795c0afe06def9c7ab5f77` |
| en | shape_arch | Arch | `46230568597d03f68efb1537738595dae05d429ae807cad67bddaee6a270c415` |
| en | shape_circle | Circle | `0ee4dc293d03117384ed71a0616071899d3673565942b74be29a966aaf30e3b3` |
| en | shape_cylinder | Cylinder | `954f6aa804f87cb6636325038bd3ae7a84cf8d931160b504a264ce8c709a5864` |
| en | shape_diamond | Diamond | `d9a994ee063234198032723c2e396eb0a4b0971f65cff1a04531d88a527612e3` |
| en | shape_half_circle | Half circle | `72ed170c176fac7568741443290429a4e60c7d0b7af71ea230d811dc902e3a57` |
| en | shape_heart | Heart | `536f497048b79006a354a9c209748b41c6b290f0a4828f128ddf23a44c2290be` |
| en | shape_oval | Oval | `027b61901828c470eb20fe583b9469a94272fa74049de22cf28cffb2cb2a19de` |
| en | shape_rectangle | Rectangle | `b0f27dc1828b87810e3006adc63ad73b3b4eb5234ef751b09870cc8aba563f18` |
| en | shape_square | Square | `80080fd16719baa3336887948309fb32baee193d8ca241f0fbb407e567aad3ef` |
| en | shape_star | Star | `53dd203913d1c183e14b334c7202edef1f41f2832cabdd8ab44fa9df9553f9c0` |
| en | shape_triangle | Triangle | `e0b16519f1ec08da6aecfe92992f5836ccf53a84f1a4eace5cb8745c746cb1f7` |
| en | snail | Snail | `367aafd88aab2121b59ae3d7a85c4b4fa324cd56cf4d6b450521e87cec50bf42` |
| en | snow | Snow | `47536ad73fc29acc2d3dd0172382cbfe7a32eb60570f4a8c68ef6b6c438eec23` |
| en | snowflake | Snowflake | `75eab12112a035f336b766695ea96e3ec2c577f735669ab196a6028864953031` |
| en | snowman | Snowman | `ba75e7619390febb3201e72f97549442c1de239486642217282b348b2d4630d8` |
| en | sponge | Sponge | `d655a455251a676799679138b30ce462af58251f11f7005332c14f9e711df6cd` |
| en | squirrel | Squirrel | `431736bf45bb343d8205486d3964a7a83991df9f4212a75520c3d4d69f125a7e` |
| en | starfish | Starfish | `fefa344fa861f5ba592611d301a8555686040a02b13848ed257dd9d0336a4967` |
| en | stethoscope | Stethoscope | `9d3632cda556fbda877f5e8a204f19fba9a800c67d29c95d407f58c19b4fb60a` |
| en | strawberries | Strawberries | `b1c3c50b61aea506fbb3128b503e9540b7883dee268600820a12172c4e20b9e0` |
| en | strawberry | Strawberry | `6daf54cbd325c78a24c86a42cec59d1a4816aeb2e531851ead9e5d0f7bb77dcc` |
| en | sunflower | Sunflower | `baed6c2c913dc3f81c4899109187a803bfcd268020f3489ac8bfcaa6999ae409` |
| en | sunhat | Sun hat | `2d978ee38619e4b053e6058a6995207956c240976becbc7697dc2c5d3c991440` |
| en | table | Table | `1cd7e09e9ae77b4e8f12f061567f5847640922961fa6d337c23d5d579b159b2f` |
| en | tambourine | Tambourine | `982a0e52507020734c0baa15bce0d691ad83939be27d04c0b08efe6d46da7b99` |
| en | towel | Towel | `721656e2668e712c2fd521fa7f2517472b29954de2b5325d4227e8394dfe5e0b` |
| en | train | Train | `eba125236ca02b0e5f3f67a3150b98b50c5a51e905dec5a3b925002151c15b90` |
| en | trumpet | Trumpet | `e24cb4f76dfd31bca8933b96cd88feaa9dc8ba27a1ce7215ff26bb48e54ffc6b` |
| en | watermelon | Watermelon | `86036686926a3728f394ebfdbeabe64803fc79519b0b7bd999ff4efadde094c6` |
| en | wind | Wind | `790ee32fac43224f2c20d973ff1b8fd79c82b8bb5d0005ce41ecfb5e5caa26ec` |
| en | winter_hat | Woolly hat | `e5cea5bde9c6d0970ea57f8fa3594a83a2b6a7060af1e3148ef8a7732e577a4e` |
| en | xylophone | Xylophone | `346d196ad323b69e896c31d60e5f61d57aeea24eca6922df0550c8b2b3766312` |
| it | acorn | Ghianda | `cb814760f6e1564cad8be1d8d1c1a078ce1cd1ec017a900d695a34e922bd6ec5` |
| it | banana | Banana | `6111c2fd0c499b4edce28aca8bd682c1a574766b784ff333fc12a1285a4bc921` |
| it | bandage | Benda | `67671073abcd6029b364542634d7c2f9102fd42a1893299d0ecada2b74a4497e` |
| it | bean | Fagiolo | `04d0d47e10e1850c9cb21f56b33481a4b46fed7c9ee6d48d025c04c922362bdd` |
| it | bear | Orso | `0b6022eaa4791f7968ba65c90d5b00a633520d0fb3cd3f655f318bdca6065739` |
| it | bells | Campanelli | `e71470d0126546e4bc51f5e6808f7028b7d819340ab5208fae08b374d5d72da0` |
| it | bicycle | Bicicletta | `0840c8723027ce945f44ba6d436577225248bc22025c541e23102a9368d8df72` |
| it | blueberry | Mirtillo | `fecae6e1c1070ca03d34503cc021c93bd4333a381140e9d2d8d8375573819958` |
| it | bus | Autobus | `5f69bb959e61d1822bfdc46f22f3e40e05347f198f82edf5d1e73ba9d91cfb3a` |
| it | butterfly | Farfalla | `2b85f81bcb892328c55031db641988cd41eb8a75c5d96067a2cdb3f04468029e` |
| it | car | Auto | `8536395cd84cc7c4ff2eb958a58216a9507c45e3dc1056a52704f1a02184c3b5` |
| it | carrot | Carota | `771e0ced84d0348d2bac5e88c067a97ea25ca571f48ffb12d8d3211c47950770` |
| it | chair | Sedia | `c46842406687b61ce67056ae7a420076517644c36b421636cb6989a84db665b2` |
| it | cherry | Ciliegia | `5844cc7fa5e2c6dfbee8b6ee0ba09ed3117a64c1d19696db11502062f5e04eb3` |
| it | chocolate | Cioccolato | `3b866c640e027a4872cb675d9f9d5840a9672f556987b1485301cfed41fa3979` |
| it | colour_black | Nero | `352bb5c0e67e6dc98c29c8385407d8e0ce5931c38358125d13cd9a2c0c4e4412` |
| it | colour_blue | Blu | `24094ca53fd1d7c8e24579af1a6d23970fee52ec5dc151301ea1548d1a5f890a` |
| it | colour_brown | Marrone | `4a8fa534f629241f66862c2f0a8a4d294f59b82f8c329953322447644af498fd` |
| it | colour_green | Verde | `3af6beaaed6156834fbac5eb89a85f49bcdf4de199afe0314912a0346c190442` |
| it | colour_orange | Arancione | `6ad124beeeca2bfb2539e1b745b6ef21ba0d3035db0ae641fe681b91c013cba3` |
| it | colour_pink | Rosa | `9064b843b22701c9ede3a21f99e193ad322885485875e8bb38c6a2e7667c046a` |
| it | colour_purple | Viola | `e6130080da6a608da945c7fb65fefb29a1d5d299a32aed21142e7cc09f4d47fb` |
| it | colour_red | Rosso | `f8724af607ec04af2b7995aeec09ad1cb0491bc518c09916c882dd0b0df601b3` |
| it | colour_white | Bianco | `4ecfbe29c0964ce405796f9b41e0fd3d5377b883498b7d5abe453dd374793ee4` |
| it | colour_yellow | Giallo | `bcfc7e97273fe05ec45a99dd956dcfa61791db8f581c46d0d46ef8032b510091` |
| it | cookie | Biscotto | `d5034d8f02f55b17c961341da412751e3b979f50128449d161b42839260ec3cf` |
| it | crab | Granchio | `f415ae0704180742e313bedbf045cad576770be62935d82d42733ea5dc70d3ee` |
| it | crown | Corona | `0c36eb5fd2e227308cebe6fd328a66c464648cdeb6486fc835d151ce28c003d8` |
| it | deer | Cerbiatto | `c96245223a01cca4cf1402005a5c612bbb486f23773aecb5c56423d0740f7ff2` |
| it | drum | Tamburo | `27d4136bf0499fc3d712dad5c510eabd0a41a1b7d55149cac59e83e94d1d8fc5` |
| it | duck | Papera | `d66d58112edf4dd28266fbdbe5625f462e2f88d41600195a37fcc423e71b4f16` |
| it | guinea_pig | Porcellino d'India | `b0d52a9589a75cfb18c3ea3825587355498ac666db38c3f3e48ca503d3bd5911` |
| it | hedgehog | Riccio | `ebb03dc06a5e898f0ceb6de3ab2ab12e956633d0483de70651093a31415b02f5` |
| it | house | Casa | `e5824a6901547b6b47970addd021f6727c385402d6e558f27fd3defa1bc679bd` |
| it | ice_cream | Gelato | `db7d255bee534a4677b85cd946d3f52c12352bb14befebbecc9ac6375c768712` |
| it | igloo | Igloo | `66117dd92c20217213f36269d378e70893e0b0b9097b07c8f7f302150572898f` |
| it | jellyfish | Medusa | `1b0c518a44959f50482fcc114f9b07a38b29d203a282d25e63b94c633a700778` |
| it | keyboard | Tastiera | `419bf0132985bb40ffe63284fd3dbb5c8dc9297d91cfbd77f601d7bef8971cf6` |
| it | kite | Aquilone | `c8baa71a2aa20b99acdeb1d4d1eafedf54389c48a55dd81bf2602bbbed149716` |
| it | kitten | Gattino | `8c7022f971e7f34b6fa47df462b3c23ea149a9739cc14c441d6801e92e586b8b` |
| it | lighthouse | Faro | `19cd8464c0d1dc7b2538a4cdbe8255ac674b5c8ed0915516817b5f7c1039a8f6` |
| it | lion | Leone | `c6d36ff809f83045611a3233e8349731e874827a57d1badcf7d2e679a9250428` |
| it | maracas | Maracas | `b368de61a389bab83c487dc9706716bf4dcc49f058af32ceb6551a796b77727d` |
| it | medicine | Medicina | `be892e2111ad9d661a9b7f0b692d362570e67b0116b59392dee924bc28f7caed` |
| it | mushroom | Fungo | `c90e9cd24790c7ff417240610cbc7478e7945fc01ae5afd8ac7f4cf518547694` |
| it | mushrooms | Funghi | `5ab0fda666b031c291fbed51d5da3ed0bdc5de6f0f5e63a44d78ce3ad622fd59` |
| it | octopus | Polpo | `afd15c272c1f558783ef9885cd538a3c3fbdc9c8acd1c983ba685d35060739c1` |
| it | penguin | Pinguino | `af43eb3224adb5086880cd21c1bd030cc004d0a9fdd42261c33300f40e00d0f5` |
| it | pig | Maialino | `fb5e3738bf398c0c4c253ae11351817411be4a40e96ebbdffb2873f0a5dc23af` |
| it | plane | Aereo | `b789af9db69488cc67078f2e8d57d62b4053fcc86cad4547fc9316018a3f7e73` |
| it | pos_behind | Dietro | `e0939354160241086142083be44bdcd2cbaf0e1a3316abd8d3d87c59e5ff7c9e` |
| it | pos_down | Giù | `b09f268c4f1b3fdd5763fc08177e824548d67584a3e44f7fba504322d713c477` |
| it | pos_in | Dentro | `f0b0c121303cd3abbe620e3953c90a81377cee99580cf9d48f6fa72b98a3424a` |
| it | pos_in_front | Davanti | `f7eb96011e4e9e8ffd00390463db14c316ed11022403f877e7ef32392457b3e1` |
| it | pos_left | Sinistra | `60b16cf4e6ee48d9cba5af2dd63fd1429dafbeab9adf69f13db1e94433513568` |
| it | pos_next_to | Accanto | `40be6d568ea67b632c9a1726ccfda661f11ebfc5af79db0545387ba213699a47` |
| it | pos_on | Sopra | `780f825dcf961b9337f9e053afa5901e145a2dc3c57bd28386c453a8f4659416` |
| it | pos_right | Destra | `5d68d6483804e79fb3f80f24294225fea65967fbbc95f6542b4613d0cd03bc27` |
| it | pos_under | Sotto | `e311b032caf7eb373a1e4e0d9be792dc18799bf157fa50d7409601f9899f907b` |
| it | pos_up | Su | `aad9916e35031aa291840d3a7803be85699f6ff2d4975fdbedc36aa4314d8403` |
| it | pos_where_is | Dov'è…? | `d573a22b0c7f72ed04a811f2b9c490b0fad0274cb90b858991a276caddb17178` |
| it | pufferfish | Pesce palla | `b6d9f16fd13067ec10823c8d5ceb168496da42689d2badb81566a59ce959b373` |
| it | pumpkin | Zucca | `7b193b743fe97d96e95f9754518c6429d1de43eb16dcffb9a41e5458bd8b5747` |
| it | puppy | Cagnolino | `5d97a735571d773ee77ac5414d0b092fa45173a70309661740b42f357dc0c5cd` |
| it | rain | Pioggia | `f093ad5071fd6d1958c57b8bbeca02b24af73263a25b91f13d2ae4463f745cd5` |
| it | rainbow | Arcobaleno | `ebd75d5d1256b690689d65ee96cadefff5602a2c76fc3bb20456a413a0e355cd` |
| it | rocket | Razzo | `2452c479a4201f19fc2b75842773d50134f15196c97810b87b71f803be4d28d4` |
| it | scarf | Sciarpa | `f3e969e32ec346dd7e7d473240b88897d8c1301c771030cf80a0d1b38a0eb686` |
| it | seahorse | Cavalluccio marino | `2997e1e847b1ba5ab678aa44d5e08a393793c0da0de626f3381c17e46eb39f31` |
| it | shape_arch | Arco | `9d5c6b7b88d4e6b8165ec428e214443c14553641dc05c9ca622764f1301a1638` |
| it | shape_circle | Cerchio | `df09cbc1abda9f07698f5b3570c814916713229ecc0e5f1ed3bf9f05683a274b` |
| it | shape_cylinder | Cilindro | `bf2709d428539df7b272ae84023430baa7ced6a51f8208c902a541aa1c6d547d` |
| it | shape_diamond | Rombo | `eb6b1156a671301232ea2fd67f82694c0864d1719d224c74cd165e4a9aedfedb` |
| it | shape_half_circle | Semicerchio | `0c357e2ac9a6f35c0a5fb85964d241f6c2d7f06cb7338a46693eed75e901e2c1` |
| it | shape_heart | Cuore | `e6355f04bf6149f1b1042cda2973d344a3dcce9acb281cbd7473d1c0c631a681` |
| it | shape_oval | Ovale | `c8c548681890cfa5a3748c4e126db0f6db39b0b182ac4e3cf94037bfed5c5cc2` |
| it | shape_rectangle | Rettangolo | `03e3d8bf55d3bf7cba99dd5b217791e83a5faf6980c1bd962507a4feb6609d51` |
| it | shape_square | Quadrato | `6c506b5042d5d67bafbffce1a62c8d3e2aaeda92a30740838b0a7a09d606bad7` |
| it | shape_star | Stella | `2508c9214cebc44ecde272ebe03f4a15e85cf9d4f39d4331ad4aabbeef8cfe6a` |
| it | shape_triangle | Triangolo | `af7f7e695f73294046a09db70dc1ab58f8a7c4f965b69a1b8b7b4186a56c56dd` |
| it | snail | Lumaca | `5574e83232174c405c7eeb9f9348a7589cde7e300015399e4696a47522d29f51` |
| it | snow | Neve | `8036448fdf39e047f2c3a63d8114c8ddd7c4be6e70b147551e4ba6be2666dd10` |
| it | snowflake | Fiocco di neve | `b6854f6053ae3b5bdf4dfd4c3944fc25568b5076a30cf3efabda26e41a7a98bb` |
| it | snowman | Pupazzo di neve | `9fbce8071d14f7bb4cb1e20cec69a518d38cc34f67c10955743f876963538326` |
| it | sponge | Spugna | `30d0c1c71fde66e6c0d54da5a3f572e459f078c5b358f237b056fa518fd1e94e` |
| it | squirrel | Scoiattolo | `966fc64e030b81bf2f93a7d47aa3a0f73881049b25482015b5784621692ed483` |
| it | starfish | Stella marina | `e5dd24d20cce4d20c32cc9305776a5e09db5a9f424080f7c6dac698f01157d54` |
| it | stethoscope | Stetoscopio | `4f73f5bb6009c0ffa7548afdffb243f1abbde6f848731881b4065c49e4b996eb` |
| it | strawberries | Fragole | `6557e67b69d3d6a9e8aef4289dce4965536e6877e0d08bc9e620cf8540e0ce19` |
| it | strawberry | Fragola | `772e376d881ff3405b5d16b8a3220428836daa8b0378c6c80769a8c28487a9b3` |
| it | sunflower | Girasole | `9875ff2866cc8c008c1bbb78b57cad02c8520e3a9322a008690b923ca507187a` |
| it | sunhat | Cappello di paglia | `93e76887c84e6ce94c89f68a54a63006c54d6a7c58c6d7472356c4ae230d6bdf` |
| it | table | Tavolo | `03bd496bdeedba9b9fdfd68907d5a5f8f752d6ed06d9984226a9a987f7e85007` |
| it | tambourine | Tamburello | `930c5d6fbe15ec9d528f532ef26256f59b2ddb47de5340ef2205feaebe85d04d` |
| it | towel | Asciugamano | `d77b315020fcffefae9df4c3b8f43444ac2cf5e92db129d54d028e9714c7a2bd` |
| it | train | Treno | `37b8fd2b8d4e6221b83ed837929344925b7dcc26e97af2dbbd9b280f86da85c1` |
| it | trumpet | Tromba | `4d781313cdcff3ccfadb591c80e4b47a2b92d2600a3d6d36d3ce26ccbe975327` |
| it | turtle | Tartaruga | `5e4f9e556e8c2b9409683c48bb540cba67999564c45d5fa05973e0f574f8e5a3` |
| it | watermelon | Anguria | `deaf6dbddb91289907527c033f6c3ebdf1a2e430fdc4bf831cbda25761cd96ad` |
| it | wind | Vento | `276dc1bd95e5c9c101e913e82e2aaed269a76789832ec5be35800c39e04795c6` |
| it | winter_hat | Cappello di lana | `0f9bfffb25774584767c7f1c6624db8160536d71acc1b73187043d2a38c32a10` |
| it | xylophone | Xilofono | `cc3cc679920a9273bdc1add0c5a3469dcf53916bd5279e6f8726f9bafc7d1ca9` |
| es | acorn | Bellota | `7dba520c0ff4b19bd407106c24aa1cf1a7bc06daa27854c5859e8db0de07334a` |
| es | apple | Manzana | `013638a4ab91c1fdc8253e2d11b0199d15f9029fe37036bacc34a9d32aca5f59` |
| es | banana | Plátano | `0e57809328840ee4059a2d67b8f54e4a2f6113453331272b425d67af721d3b37` |
| es | bandage | Venda | `9175803a3d309fcef2199ee1c32b5b44822461509811688a9f2f22b316066a00` |
| es | bean | Judía | `7158de014133592d692eca74f21f0f54796c3455b7de6b96f466913335d7ab9b` |
| es | bear | Oso | `51d91119282c17305686749fb6c8136dea67532e30e4fbddf917016e6114a7c7` |
| es | bells | Campanillas | `5a8da8ca7ab680c4b87e6883718d4ad33d016ae04f81ce2771128992e05f8ef3` |
| es | bicycle | Bicicleta | `e20bb6ee68517e599788b2ccc32ee6a18166bed62ebed8889ef4e538e28b6474` |
| es | blueberry | Arándano | `d3592d3456d23e7851029ebaf0d7e9b185e7fe5288dd5ea4e3057f8d1a9a28c1` |
| es | boat | Barco | `62c40287d5ef86e2a5720de59c50072fa8275bf9584b305b9628c295a268e876` |
| es | bus | Autobús | `dbac107c1603b7962efb211227cde60490441f79845c3b26cda8ee94533e3c69` |
| es | butterfly | Mariposa | `c39a2af48bfdf51f3044d04c6609dd008a1421f950cae32b8fc562cfc98a0c01` |
| es | cake | Pastel | `78c74551670fcfe620c41b06e1bdac25e89be91ebaad550256893aa3e8c27545` |
| es | car | Coche | `eedbb1f284a323528e9d7b4e0659ccdafd723a17d51e3dcd32ff5b6825d4382a` |
| es | carrot | Zanahoria | `7958ff1ac2711b250cbb9f468dc3c33d10b351ed0570d332289d2f90d4fba12d` |
| es | cat | Gato | `bcffc5ee2fd88c4a11caa6796a4bff229e3550f3bdb04eabd378214356f555ff` |
| es | chair | Silla | `378ba6209e6d4e71fa38bca5ea6aca15736f713e194abb907a6a8800a93f91e6` |
| es | cherry | Cereza | `9129adb9943fe33e91ee1b2583584a32a97234b37c1df0aab3c17890a56474a6` |
| es | chocolate | Chocolate | `284a42fcddeb144fbc070491cfadd7a086f65f980abe264a65bce0514d1824f8` |
| es | colour_black | Negro | `93950a585902c91062a569ab02683a03f17ad2427b2d1d7e0b5e8aa41892aedc` |
| es | colour_blue | Azul | `f9feddd862fdb37f19f562f57034594162304407bc5f88714f66af06b0c337f4` |
| es | colour_brown | Marrón | `db126064b6b1c4aa691626f5bebdb894eb693b71397c51559016b981a657c1a7` |
| es | colour_green | Verde | `e085146682acb9d91a5fd796623a3c8ff65a8e29881fef77b03d8f300e547a42` |
| es | colour_orange | Naranja | `c527183a7859c4bda520f5fea135d3f4e383f3f6357d8ab872db44fad3bbaac6` |
| es | colour_pink | Rosa | `6e0f953154f08ef5fe3ef73585b35e81d9f19a0bbfceaac111b9012e6739236e` |
| es | colour_purple | Morado | `e2241097799c19fba745ed1666d6a5d422f38efa5851a378a4e0ed5d14772b35` |
| es | colour_red | Rojo | `77eec657e5cad22ffec346828ee9c5ebc68f24c2803a8c8f24ed22c78b0d1c75` |
| es | colour_white | Blanco | `89b69fd12a3526b1ef52f74a9edf06436be9ddbf8a72966202b6c8b2be095bc8` |
| es | colour_yellow | Amarillo | `98031329db78d4a072be0dbb906fb8ee58bc278c8985b5c1d7b23f06b8da0960` |
| es | cookie | Galleta | `2411342e77bdb8c39830567cb5ff82ff2732d5a47ba4ceb7dfd0ea3da48e9ab2` |
| es | crab | Cangrejo | `220dee2bb987a1c1d883baf5d090668edfd68b5bb831866a703d51357e266e0c` |
| es | crown | Corona | `87f5591c61b4abbbc09b7df1f229f3e52f8e006816cfd2b0f8aacb7784ffaa2b` |
| es | deer | Cervatillo | `93eede6f0df3968f2aa32e3da9733e132c70db8ca1aded0aec3d1fc01067bb7d` |
| es | dog | Perro | `ae0ea57577c00aa1467fb389f1c6fd4117f957b5ee2ed66e46cc758b84a88a90` |
| es | dolphin | Delfín | `1051076d79f2d2f5780ffb56225fd83ef454c61a1ce5f0cfdf357233bacdae44` |
| es | drum | Tambor | `844f82568df0afa4be027838728b56bfcfb896242b1775b472b6b0b624da2973` |
| es | duck | Pato | `afe948c07ef75d298d11c7e51d77c1538e96d1d035efe467352118f085f0e9b0` |
| es | elephant | Elefante | `eb7483f4ff52228601cc1110954d456feaaa74cbd2bc8f75618b23baa7adb387` |
| es | fish | Pez | `910521d81dd2e5595a91d22ef976feaca856946928ddbe1b88511536133dd137` |
| es | flower | Flor | `ab2163bc98145f73f7a6e4568fcb6b2f70f1606881ab5f3589e7d7cb11f562e2` |
| es | frog | Rana | `cd667d0e6f575750a9747073109a6cf138a7cf9198f2322f9ed81ef683db88d7` |
| es | grapes | Uvas | `0025ee510f4ba91ebe15e4b4cf6171959f4c174ea68787303429187fac1c95ba` |
| es | guinea_pig | Cobaya | `ba3c7555bc8fb50f82526d2f9a495c136dadfbb85e825e9edb45eec612a4e4c3` |
| es | hedgehog | Erizo | `5e9ce60d3066534f5b91e6d72d23c001e7cb2b37e024e89943ede9e90e213ceb` |
| es | house | Casa | `aa9344de1177f7c134ca37b2b0a5a6e4b65dbbb4b578154bd852cd9d4b456505` |
| es | ice_cream | Helado | `19a728df7028d7996b874f346fe104889e3f5d57e286cd9ee96b0b5200af64c3` |
| es | igloo | Iglú | `a17d636b03c657b608b6d9a129dcd6a9e0ae32eaeb77210bb7307c66b80d5152` |
| es | jellyfish | Medusa | `13b598006eac3b39ba8f2cb4a1a40caaaaf881a764982b41a0ada337d01e6ea5` |
| es | keyboard | Teclado | `a214213472e23b112ebb1ec86478e19dac06954e0991896e2eb68a7c152c6628` |
| es | kite | Cometa | `9c7bd06b72be6a48c65c343508ec517de1626bac58df0378dac90a3e1a8cafb5` |
| es | kitten | Gatito | `e9938e1479061510d7e3b0a2f1908e4bcbd19bc12e226150c8c56b4100cc1b20` |
| es | leaf | Hoja | `e57cfc4859db0e90130d933c5d32fc0f02216361813ed448237b894d76176d78` |
| es | lighthouse | Faro | `be9c1e0694dc76a36770c5b6ac97b96eefc45cd8f5717cfce503bb8dbc33ad0c` |
| es | lion | León | `be6f3230d7fe8c400dd972613904a9fd8b298101992e14f2d66d61998db8c8bd` |
| es | maracas | Maracas | `4f8d7326ed5268fdd8c6b777b52a647c5db540f9ea6d6c06a8c110bc5b160e74` |
| es | medicine | Medicina | `da774252dba522e9103d6cd298c72e5030b7dc17c84ccbb836eb7308c8ee2f01` |
| es | moon | Luna | `2fa43287347ba8100c2b5ae284e6e2cdc039298e890e9383942b0555061bd9f7` |
| es | mouse | Ratón | `83fe21158179fb4dd22e52cc41f8b20dddf06b78b7102d5a08282afce137a5b5` |
| es | mushroom | Seta | `cb06c79585cdc340281dc60d8acfed0cf15cd9af3a0fd7cdb7a34f8633abb8ad` |
| es | mushrooms | Setas | `5c1f916e315d07426c7613dddcd22387a08b07b4029b26d147a0004971159aeb` |
| es | octopus | Pulpo | `207d48ebea4a42f733e8a0e76b890e2f8214484964ee3bd3d84e356685271583` |
| es | pear | Pera | `52e953180e496eebdbca2f9d60f93bb67812153003465199226d6b1ceda9d3ff` |
| es | penguin | Pingüino | `0e33de7cb8e01f00ae38ac07a35c77a593c445ba52d4497c8e535b7b1ff961d3` |
| es | pig | Cerdito | `4a7a8a0619728b5bfe78f99f224edc92ac335ee3653b3961f76b350319b05b22` |
| es | pizza | Pizza | `01078d2107cceab71ec7ad0987cd97f86dc04c1dadb0f06f2d6b46f5a8318330` |
| es | plane | Avión | `7929c1e0b6825c203064684d76dd88ff82c6cd0414a80fe4a6a0ba015d88d4d2` |
| es | pos_behind | Detrás | `db8584ff9435e5ff7de7b79902df3c48292d9f249a57ccce5f295160cacb8e55` |
| es | pos_down | Abajo | `d2c950560a532dd363abf38e39765a1ddbb6a8ca9a736aa2574fcbfcb64af3ec` |
| es | pos_in | Dentro | `8be9a1c2d01a36fcbf73936be8212e7e73357b5e2b29e7a213355e2b68d140d2` |
| es | pos_in_front | Delante | `4a9c7bccc9de9ae1564e531b4595d8d277673a5a876f0cc2439d92413c82b098` |
| es | pos_left | Izquierda | `bfef5c536bd42864c160bd233f8b8657e500089695ff759040260e86c56b1193` |
| es | pos_next_to | Al lado | `c77c6425bb3959effc4ee03d2e6fef028d5eac83e6c55fe887445cbfe448b37b` |
| es | pos_on | Encima | `4fe8cce98a4b2fa22d6b05021339ae33dab477d7da085af3c6c486ef424ab798` |
| es | pos_right | Derecha | `75eaebe7e841c2fdfc7d3081cb25ead7e3aeeeb140985f07f31aff6ccc20885e` |
| es | pos_under | Debajo | `4599fccf4039745253e39097b6f17c2c9950041e07eb53d66f8b520abb209873` |
| es | pos_up | Arriba | `513856ce6ede72a067821ee58226ff7f9308eee41ed187bce732d594fb7bfd20` |
| es | pos_where_is | ¿Dónde está…? | `472c22a9d73df5c88c884d11cb4496a24ea7f28c7cf9573dd5785f429c7729eb` |
| es | pufferfish | Pez globo | `e737cd8f17ed9323ce3ef7eed031dab26839dbcf3b18ad370f655ccdd13bf794` |
| es | pumpkin | Calabaza | `0034716129a7e41400542ad3b84a8abe859f185b8b020f1d52541f986c8ddfd2` |
| es | puppy | Cachorro | `ad6357c042f5b7ff82c72ac5eb757894fb60a6f250527dfdefb0b8a02f87e2c0` |
| es | rain | Lluvia | `6cc686a967727d8e1fc4f801815831597ffc898eb4a16e3f6418e9008b74c640` |
| es | rainbow | Arcoíris | `ba4d3e31672fae4a5fed8a2321ed6ac625217f3e88e490ae4681117ff28638ef` |
| es | rocket | Cohete | `8d678968fc8a5e1f512a89c40a3a25c25fdf6b136499af5c3c622478683ee2ef` |
| es | scarf | Bufanda | `54304ee3439d17a4d577a2fcb415c2189dc6482a5a3b30675481fc364c1e6728` |
| es | seahorse | Caballito de mar | `dcb2d1e8b8b039b9b1bc4582dd592ae77cd193c5ff61b4a0d4ec0c9fac980f95` |
| es | shape_arch | Arco | `96f42a8fedbc6545de2075313587a576ceb3ce7bf916fc4fb5b0e37dc162031b` |
| es | shape_circle | Círculo | `97d2c8e8c71de210f3dabc0f67883763f40f3fdf0786687972a838528ebe00f9` |
| es | shape_cylinder | Cilindro | `197c1dd98978de6a409c9f208fbfba5bf7e8fa9b3289d1200db09cd5e2290c9f` |
| es | shape_diamond | Rombo | `717621faa2929795c31acf99b1ca9c56ef971e3d0061bbfab345694b76843cab` |
| es | shape_half_circle | Semicírculo | `6c187d62a9b980bcf3b46f49d27c4be48587d288e083c55a8d8074437102c293` |
| es | shape_heart | Corazón | `9710f4399bd6414eeebaf4c8a0b14dd46c83e78d64ff17a14a065e176530e5f3` |
| es | shape_oval | Óvalo | `36efd2b20fb7432566be0712303f4c0be3fcbd25ad7c9eae06c7233e33954eec` |
| es | shape_rectangle | Rectángulo | `bfa18ecb1070dcfa11841e3af9c805bc2b948c0e3c1b2950f5b3af83a542919e` |
| es | shape_square | Cuadrado | `de55f86d38690082e8301062f7c3d30e8ffc9d8d18c5fa035872defbb6d9fdd2` |
| es | shape_star | Estrella | `d1504b9b027284607ee6de508622e42c177090894de52ea8de7068b739809a08` |
| es | shape_triangle | Triángulo | `b91cf646e2c3fa8a9e9530ee1c0a956f18c61a01fa7abc7cb2ec1c92b2f06417` |
| es | snail | Caracol | `2e12ad30e1887e7c50e781d9a919c9d2cc6bb54c2f22d3d92f94df3c0e4c642f` |
| es | snow | Nieve | `fedce47944981f798d61b1f4d2c6e979dcc2c5fc437581d26885759c4c348770` |
| es | snowflake | Copo de nieve | `da7e9ab208a8872003c27634b0b6cb0716524d118ed6735e3a21ac86f67db658` |
| es | snowman | Muñeco de nieve | `7451b4a8a47322f42f3d712307052224e539883d68b2a907d5ecc8c96d2471d4` |
| es | sponge | Esponja | `f2f1e0adcde019b8dd07c8119bdf6cf57368e0eef4b83083fa46f8a59407985c` |
| es | squirrel | Ardilla | `5ead9337008dcde362e7beb2e08d27f4f55ed8798dbb71acf33dd354abc1b9ad` |
| es | starfish | Estrella de mar | `6dd1a80d296011fa72566fb338f275f561471de90f0bdfef32cbb1bef48b8322` |
| es | stethoscope | Estetoscopio | `2bee1c586d4bbf1533fbf5643e5958cb9a9307c5cfb1098ca0d0ada1aa5bf209` |
| es | strawberries | Fresas | `ea4fae772460c984b5168db045d5690c22ee7be53d9b7ef9c3842ab74d87bc33` |
| es | strawberry | Fresa | `3235eb89e20f1bc4fcd30a3406df2c8f47083551858b5e709616f27549ba73dc` |
| es | sun | Sol | `3ec7410372b073861c12a7b11e84d47c51c4ff2673896d786502efb8a6e3a859` |
| es | sunflower | Girasol | `01ef3b566660872000928f26b80cfc24b0e6259b0e3df53198018d042bd74866` |
| es | sunhat | Sombrero de paja | `efb599c313cf47e470e1fdc1e31d912b1e9822e336b0af1ec0e569a677f0bc1b` |
| es | table | Mesa | `9af759758adf4108cb950e34d4bed2fadd184d5537d63dfc417d4eb6803376e2` |
| es | tambourine | Pandereta | `7983816c6ac117440e2e4f7714225a3e0e44f69daa79ed1ede2a9604f63b56ea` |
| es | towel | Toalla | `baa508075c4e1c1ed08df742feaccb78e1aafbf20dde83ffba9e0727236996fa` |
| es | train | Tren | `0fbb23bf3ebdcdd7aff185005c468eb958331829052f6a895607a865a0b6781b` |
| es | trumpet | Trompeta | `41d9febed9f042e976bc0b82fc1b4943e622952775d31b6db3b6ba7356d1cd8b` |
| es | turtle | Tortuga | `1d9c5a18293327bfb21eae107a5b182966b2d9f2a5d393d5d2c434a94b613790` |
| es | watermelon | Sandía | `a3faedeceadd484dd94e5c788350fe7d85d27f9428f47874987be31c5ab16232` |
| es | wind | Viento | `f490d0b052bab8c5838fae35f1516b3d94ad96a7abe6307dde646b86da824275` |
| es | winter_hat | Gorro de lana | `e8ed20e2c72ecc19290cf66d9bc25ad2bc9f263e75128ddb53fbff8f9c5fdb27` |
| es | xylophone | Xilófono | `6536ed3b1646ea41c7932f3022e08a9c71c33c66734ea228d862606f2a44cdb8` |
| fr | acorn | Gland | `71bc1c0c2ccd7ea1b63be2faf7f79350b3e956ddce2c1d718531ef8a70679c31` |
| fr | apple | Pomme | `52a9cec09972d0f6694911ff33d2357fd229ab4dc651c3bb3554ab3e467e3e1c` |
| fr | banana | Banane | `804f255f1e819a4c96e84a3b5685f8b6d951ad3ed0ada11c14df49c6a1cba776` |
| fr | bandage | Pansement | `195a4dd0b93308d544d0d815885c142e152b78be31e56e74dac8f3348589c6ae` |
| fr | bean | Haricot | `85ad7978cce9677b8a179449d00943886a04cb7e8c03ae850231733897826479` |
| fr | bear | Ours | `72f942b4c28d1df45b5428221e9f2f39940f8959d7ac696a3acc578f8f1529ab` |
| fr | bells | Clochettes | `90965b3e184376bb5a12937416353979337f22dee34353ac1fce56cc7e017196` |
| fr | bicycle | Vélo | `d83dd94356ab9b4922bca4dd73774a16761744320ec10acb94fea014df14a83a` |
| fr | blueberry | Myrtille | `574d0849b5c5bab90e4b6b446d8b1488a630cd2897da55629e11a13d8f9273fa` |
| fr | boat | Bateau | `9c44fd3dc70ce1c072d2cbd2a3ebc58e7dec9824473fc2b7023a9d5893c6fd10` |
| fr | bus | Bus | `205f49ee5fb17230df4b8595b9073152908965eb0ed6b6c9b4c618b9a8a4bbf5` |
| fr | butterfly | Papillon | `a23a6592d275265511eae68f8324f0f138964d0cdc615c8bf7da809441ae4cc1` |
| fr | cake | Gâteau | `fbc9fb58bd06af02fafd8a8f8b18918daed4ace4c9b2118d9110af81a330607f` |
| fr | car | Voiture | `92fc0dc7d7a43f10fa6784411c571a80b2857c277dca40c4e95e073210b663cf` |
| fr | carrot | Carotte | `231b14a02b52c6df9df8ff88b47ad661203f63f8cfc4ab6c35b4ea5a1d9f03b2` |
| fr | cat | Chat | `af5b161403c648327c503294e3fbba1595dac087b93430af02665cad124ace71` |
| fr | chair | Chaise | `bcb7242f7bf414bcc8727af4469fc3a01fb7a5179fd1ae0d91264bf765107b71` |
| fr | cherry | Cerise | `ed80c0493d5e9bea1b4b57c5f67ecfa2e0e5d8c604f07b4893c35b30a1f42fd4` |
| fr | chocolate | Chocolat | `08b71e26e61c62fb5f0f4ff8394ae20a91377cb0109a28622e4f339a5b88af40` |
| fr | colour_black | Noir | `aa2314e8649cdc8a7f77c5a996a10f9334247def583303a3147412b35e5cd9bd` |
| fr | colour_blue | Bleu | `1a2794e8d16faa26060b3873b1d528932ee261b24f31603b1049b48e3040fc46` |
| fr | colour_brown | Marron | `fcaa3f1a7a9eee42d5f00fb701458853c2d85225b336cf56c326ee7074bbbe4a` |
| fr | colour_green | Vert | `ba49a48dd0ca0128730dc38100c4dac7ad3468770217c20fe3bd4265a30c91dd` |
| fr | colour_orange | Orange | `76d5b9964fc9856aa59d27a835a0f77da1119026efb97a80d00f55276a741316` |
| fr | colour_pink | Rose | `5c7c881174d6618fb5d4973347961fc79c011cc5d03946f036acaaa1d19f5c6b` |
| fr | colour_purple | Violet | `07659bad37a191144eb552e3c561dea9dc681153d69bdeee7b0dee52a1579e37` |
| fr | colour_red | Rouge | `7ccd8d847968db55eab09764f65b7eeb0a5218ded487b672d35a0a5eff5acb0a` |
| fr | colour_white | Blanc | `062f73c6b31880c26d9c6f4e308f86906a378839f0a4df21be1b652f694e0e64` |
| fr | colour_yellow | Jaune | `112758d98d4cc8a993d5471d04e4fbf3d38745be62d80b1d782699776ba5a62e` |
| fr | cookie | Biscuit | `8b85143471375ad517d4d275d0ae564d7bd76beb93f513b1174e92f71af842b3` |
| fr | crab | Crabe | `7da9ed0e90d2a16c80ef27a6cdb582af58390e91339425abd339d5ad22469179` |
| fr | crown | Couronne | `8fd8954952b91037ecf67ff59b955f6db915f1949da782a330fee940d8ff22f9` |
| fr | deer | Faon | `ff3489de3121af6403ff5446753d7e84729582d2bb052ae51987d3c382be59bc` |
| fr | dog | Chien | `b6b3d1a6b558e3e5396d9fd90c8345a54907548ea111e3f41ead4bd43c9a534f` |
| fr | dolphin | Dauphin | `d2b4d66b03fc0f6f23f8999860bd7934df9751aa25a657bd086e432761d1cb9d` |
| fr | drum | Tambour | `fc66b5eadd72f15ce7f4ad3e1371391351c455f45606e464dc8438aaca8eb9c8` |
| fr | duck | Canard | `98b14ebef67c0f54377f000ec49ce53593c2672f4a44674eb244417990dc4846` |
| fr | elephant | Éléphant | `2736673e8276ec75af03014d74b812f41cce133dd1ca71c6816d70b7df011a1a` |
| fr | fish | Poisson | `5b3790cb48e68359afb5e013fbaea1fe275365d2e05542ca8f6f3b4a2641b434` |
| fr | flower | Fleur | `88461128403ec221018554d00ff0a1ada424d88e6f4d4a57c765fb69cfc23e72` |
| fr | frog | Grenouille | `218d671f598eca7a36b255b152cca6db806237f75e79f064dbb9e2801842d498` |
| fr | grapes | Raisin | `3b3c9736595687f9b2299757c067d55962d8194ce0520295b84b6b9515ae64f1` |
| fr | guinea_pig | Cochon d'Inde | `8d556dade2087c1209c51870e92f2b5a960a25165ee19d68eb9b8aec68d6fdae` |
| fr | hedgehog | Hérisson | `e86e1061fad8478e635d59be8e8bd79db60444a63f43417a91d69afd6dd02e6f` |
| fr | house | Maison | `172ad229c084f5cdb01826858ab92b52ec1afe3b38022e7be774b1719acb2310` |
| fr | ice_cream | Glace | `f58b74ebf4ee679ad4ddd9c5954f58fc9cd4a8ac0e898ff8df78a0936c6c1d72` |
| fr | igloo | Igloo | `354662eac285f63e8c25c461a24781bb7f4565b9414819006ed5367adf7cd23c` |
| fr | jellyfish | Méduse | `f13886c9c784ecaf5f90820ccffed34bae9e3a96ee2841d81f786ad18d05c481` |
| fr | keyboard | Clavier | `b5d0910047753a8808375eb97abad6203edeabd2c775bb1d412ccbb8bc7c269c` |
| fr | kite | Cerf-volant | `bceceb35b0ff3a7223c32b36b6adf5a158722482afcb030bfdbaa2698476f761` |
| fr | kitten | Chaton | `cb2eddb0ad605591e9fc469d66a6feb51242e9455af44133021908f6ada10302` |
| fr | leaf | Feuille | `f65c4841412004c0db9da10d3df3038d8955294c89a64939c46d4afde7486840` |
| fr | lighthouse | Phare | `b618581e11dcab800e8a7825882861c536f90d0935796a03b02c2847ed037bf5` |
| fr | lion | Lion | `6c0e8c0daeb1f8177de3f1f85daadeb1acfd2a9b97a8dc1943a15f1e4393e38b` |
| fr | maracas | Maracas | `b82c3e8eb33edce6661fbf0c671c32257d176fd1a49213cb854410fb6c7b4539` |
| fr | medicine | Médicament | `12ce44c871069cad56200f84cbaadb9c043a7585562fba0a1bc6c656e28cd8e0` |
| fr | moon | Lune | `d9aca2d0c8c9edf21c0028e6d361ddbb349679e59bae4dc5f38acdd8b830b5ef` |
| fr | mouse | Souris | `fcd0d6e63c17568097de28900e942ba6c44c9616b2545bd14b24de54d3f7a8c9` |
| fr | mushroom | Champignon | `085e4db1f77d6a49fc50647c0b045469df0c309f020762e3659ebdd16fa57080` |
| fr | mushrooms | Champignons | `9e8a6cc50055633af6a47d8d6784bd67cd07a25702ff9b2a40a29dfe7eacdf59` |
| fr | octopus | Pieuvre | `d83bf842fc628a161e37d78b9fb77603fbce66bd27fbe0de954d7f729b29ce1e` |
| fr | pear | Poire | `532d1d582b187582617f3f57edae957de6882a9e9ee11019a432b799bd1ff74b` |
| fr | penguin | Pingouin | `35d3ca10ef323f093ea04145eb68362c85e26739556bbd99a79141ee36b427bd` |
| fr | pig | Cochon | `a7645a7971595621acd87d7c4a2997e1b30140ba981793a8bf703b2ded3403de` |
| fr | pizza | Pizza | `49255917f62dec4db7ecfae738f541fe1497a0c99d01cc6945b028fd29f62b0e` |
| fr | plane | Avion | `1f5470b3528820edee779ba515a64540bc4d10561996eff560252d6ce77924ad` |
| fr | pos_behind | Derrière | `b50bf579f754d20c04a67b98a427c77bd0c31169fae77d74643baa9c97ab237e` |
| fr | pos_down | En bas | `6bf12dac959d710dc4fa823bd345bfaba72839af1fbd5ccb473e2d7f2d3c7042` |
| fr | pos_in | Dedans | `c86f8d30d806ce1cac9b8cfed997d1a3b7ab496c2d7f774472f02e213dbadea9` |
| fr | pos_in_front | Devant | `ec789b78759bb6ee39fdb19df0a6e8f492edf2a4b5e5c1c49c73885d9df86b48` |
| fr | pos_left | Gauche | `8361973c381d714c4e59e98a6027b60ffbc6476b40bb32af4656a35bc11c83ac` |
| fr | pos_next_to | À côté | `bf1ffbf54e1be4c9b2f1bfc742c9428bdab01fab054f7b4861bcebc22eb10466` |
| fr | pos_on | Dessus | `75f84b8382ff62777112c391a429dc7d6ea375b6317d1f04eb2e6845465dd036` |
| fr | pos_right | Droite | `783e36cb44e1bf4dff33b69a746fc6de3832e42eb2b5f63dcd45d6ad4d65aac7` |
| fr | pos_under | Dessous | `686802a016861b902b5e3872363649d5721dc3076ca5b2309ed488a79f7b2a74` |
| fr | pos_up | En haut | `8eec830b653ceaa35fdf78c77d659c9f5f97aee285500af5da72f31821e85eee` |
| fr | pos_where_is | Où est…? | `ffc7cd5a273e24a033a34355ea277930901a812ba6457e1e09b0f3f243f862ee` |
| fr | pufferfish | Poisson-globe | `42e6c77a58c44906026409628b9f1122a783a4234bcaeb9615b77e9b8480593d` |
| fr | pumpkin | Citrouille | `629446638d8e061987f6e3e4839ed5c3c9840fcd7cb04d08060678b66fda7308` |
| fr | puppy | Chiot | `522e561b7d2d3b1cd5a7017a8547a663fb1306c505a35a51a2d1c2195a552a1a` |
| fr | rain | Pluie | `e27841b669a2cd3518c915f4867e4624deaa2445f137915eae6f68c72961910d` |
| fr | rainbow | Arc-en-ciel | `7c660751677880bc5200973feb8330c060c045a38a06e790cd0a95476abb7e8f` |
| fr | rocket | Fusée | `7322c430f000f4044300682be63fb2d2b34f1ce7bb5dcf7f17e5a6d5d00992be` |
| fr | scarf | Écharpe | `336f164dddc890edae1b99b45bc8997be222beccbf661667bf146e15994c05e8` |
| fr | seahorse | Hippocampe | `bd963ddea8617ebaf0367a95c4aa7e17caca3d2afabfe84ab363f9cd9f551261` |
| fr | shape_arch | Arche | `4043495e3bc123747ba13a74127c3ffd1a090adbb21a8fd25af0502832aff7c6` |
| fr | shape_circle | Cercle | `cf21b381021c4bea0c5d90a4f80cfe2cc7686ca6ff0d3e2679d7705cb117152c` |
| fr | shape_cylinder | Cylindre | `8ce8bcd9a97b60db11954e278c8ea04c105d40bcdd82f8da343a7a75cd1a7e6b` |
| fr | shape_diamond | Losange | `af477f96f4bf7d6cc1bea7670a495e639b4ff5698e1af3b10485a1a82fdba869` |
| fr | shape_half_circle | Demi-cercle | `9a128248f31ddbf6793643f0d23dd94656e12b0c7db84b7813326f22a40ded91` |
| fr | shape_heart | Cœur | `c53a232397c6347a6286f669753c5f1dce9ef07746566d0280692c29b0cb23e1` |
| fr | shape_oval | Ovale | `4fda8b5e5ba9e9d0f6ae060cd3734960047f35a9e97449d004e39c5a8017c57b` |
| fr | shape_rectangle | Rectangle | `b713ca9d583564030237579e8db8d0af75aca1ce315da12b70dca530b43fa01e` |
| fr | shape_square | Carré | `6d684c4bb22a959fbe682f52c0290cb0024a76eac1d3d2a783ed589fdbfe4f69` |
| fr | shape_star | Étoile | `914ec6d64dd5af996a5a6c5ceb0bc748a719410fab31c6d6b49fcb48aff43210` |
| fr | shape_triangle | Triangle | `760231574324c34790b360f0d9d8a437a0997b5a70ab2a9b652cae9cda1141e8` |
| fr | snail | Escargot | `d1ea9a507b9b9f12548b30fbbbb4cd94b00ad3fd2329abfd8ea188a37a83cbd0` |
| fr | snow | Neige | `eb8c0862f25873e5b438269211dc175c25ee84bb910abb066836330bc623ff3a` |
| fr | snowflake | Flocon de neige | `98ee9bca0b0bd90f103a0ed712cd6a2e2a372ad014a441f2d1012ae6fd8751c5` |
| fr | snowman | Bonhomme de neige | `a88b98cbe6ca72d972b3557df7a23989e66782b87b85e5a2cd7e66b7fe39de4e` |
| fr | sponge | Éponge | `a340175e22f541fa19fff890f9a95d304e9ddfee58a250d97cfeed894ebfd0e9` |
| fr | squirrel | Écureuil | `4e67a77687a8c8c2ab15abc68fdcef0ac5eece0a4060f11dc2ddfc5d1d4bbf45` |
| fr | starfish | Étoile de mer | `415bd6fbee84218939903c09cc279c32508458521471e92eab56edd390b57549` |
| fr | stethoscope | Stéthoscope | `0645af28bfab424bbbbd0b15781d8f974ace318e5e17f24bbf1a506e130be0ac` |
| fr | strawberries | Fraises | `9cde3bf642ffa7dabc10f73c6555e0fc92bcddb0dea595254688a06e4346dd3b` |
| fr | strawberry | Fraise | `9cde3bf642ffa7dabc10f73c6555e0fc92bcddb0dea595254688a06e4346dd3b` |
| fr | sun | Soleil | `ba86747e14aa35ed8adc0415a12af9c7b6c9368c4b93602ac75e27b91018c192` |
| fr | sunflower | Tournesol | `b1fcd965890b93dc3427d213a61c3a52917ed9b6bb14c4d381c21dcd0cae1b66` |
| fr | sunhat | Chapeau de paille | `81c678d7ab2bb1ad14b1ef8d9e466ca6850f01f90bf1d68bf12c5cf4f753dbd3` |
| fr | table | Table | `d05c44367d812bf4fa689a6a422f30fd65588dae87ba61cdd4c13c130ef91c92` |
| fr | tambourine | Tambourin | `882891ea487876cbd28b21d29bee03b8997f8462aa0b91a41c9a0f89a100b821` |
| fr | towel | Serviette | `34c4dedc33aae03a8ff422bf55e710f0d67799f0a0bd5c9c9bdf10ef490b2db0` |
| fr | train | Train | `812fa30b30fec3bf112bffeb7a3df21dfa7a9fca35654fe88d43d0cb4e01d7af` |
| fr | trumpet | Trompette | `7dba94e8a2f3693f90ffd533dd59f2db0150c9506b6955b87642cc3c12a51a94` |
| fr | turtle | Tortue | `f8997a8a8a434be5ccb609aeca792bd295fe2441dc13e39a43a1f9c045086f5e` |
| fr | watermelon | Pastèque | `c7e4fdf6272d04237284b10bf3f15a179500ccee401f27c917bc30cada19ee31` |
| fr | wind | Vent | `3d3e1acd27869c4517656675c8b920a7685836feb785cbbb6651cb3e09848308` |
| fr | winter_hat | Bonnet de laine | `4adaebee615d46e0ee98e17909070ff29423a45a07e2242b3ff164a464688de3` |
| fr | xylophone | Xylophone | `865c337721644d1280ac5fa927a5cfc72ad0a6ff28618a46a3445c6d6ca57a8e` |
