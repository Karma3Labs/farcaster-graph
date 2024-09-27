--
-- PostgreSQL database dump
--

-- Dumped from database version 16.2
-- Dumped by pg_dump version 16.2

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: pretrust_v2; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.pretrust_v2 (
    fid bigint,
    fname text,
    fid_active_tier integer,
    fid_active_tier_name text,
    data_source character varying(32),
    insert_ts timestamp without time zone,
    strategy_id bigint
);


ALTER TABLE public.pretrust_v2 OWNER TO k3l_user;

--
-- Data for Name: pretrust_v2; Type: TABLE DATA; Schema: public; Owner: k3l_user
--

COPY public.pretrust_v2 (fid, fname, fid_active_tier, fid_active_tier_name, data_source, insert_ts, strategy_id) FROM stdin;
262563	Lama Boo 🔵⛓️	2	🥈 star	dune	2024-09-25 11:22:50.782	9
20442	Talent Protocol	2	🥈 star	dune	2024-09-25 11:22:50.782	9
196215	Sloppy.⌐◨-◨	2	🥈 star	dune	2024-09-25 11:22:50.782	9
467347	Kreept.degen.eth	2	🥈 star	dune	2024-09-25 11:22:50.782	9
474817	attilagaliba.degen 🟢	2	🥈 star	dune	2024-09-25 11:22:50.782	9
13030	アクセク	2	🥈 star	dune	2024-09-25 11:22:50.782	9
1898	boscolo.eth	2	🥈 star	dune	2024-09-25 11:22:50.782	9
352787	Meesh // 🎩💎	2	🥈 star	dune	2024-09-25 11:22:50.782	9
838	Luciano 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
192490	musicguy.base.eth	2	🥈 star	dune	2024-09-25 11:22:50.782	9
9820	Tony Sellen	2	🥈 star	dune	2024-09-25 11:22:50.782	9
20931	ZachXBT	2	🥈 star	dune	2024-09-25 11:22:50.782	9
4482	Deployer	4	💎 vip	dune	2024-09-25 11:22:50.782	9
284679	DV (insert a lot of emojis)	2	🥈 star	dune	2024-09-25 11:22:50.782	9
4973	Irina Liakh 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
281129	Studio Captain 🎩🐹🎭	2	🥈 star	dune	2024-09-25 11:22:50.782	9
389059	skantan 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
14836	Ida Belle 🟪Ⓜ️🎩🫂🍖	2	🥈 star	dune	2024-09-25 11:22:50.782	9
4312	anett.eth	2	🥈 star	dune	2024-09-25 11:22:50.782	9
214447	YES2Crypto 🎩 🟪🟡	2	🥈 star	dune	2024-09-25 11:22:50.782	9
306175	Lolaa 🎩 Ⓜ️ 🎭	2	🥈 star	dune	2024-09-25 11:22:50.782	9
348611	AlleyTac 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
308220	Odyssey Of The Heart 🎩💎	2	🥈 star	dune	2024-09-25 11:22:50.782	9
470886	Hieu Vo 🏹🍖🧾🎩 🐹 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
738	$ALEX Masmej	2	🥈 star	dune	2024-09-25 11:22:50.782	9
307705	🙂 lewis 🙃	2	🥈 star	dune	2024-09-25 11:22:50.782	9
6631	Jorge Ordovás	2	🥈 star	dune	2024-09-25 11:22:50.782	9
456555	Camila 🫂	2	🥈 star	dune	2024-09-25 11:22:50.782	9
11517	Vladyslav Dalechyn	2	🥈 star	dune	2024-09-25 11:22:50.782	9
375245	Chase Sommer	2	🥈 star	dune	2024-09-25 11:22:50.782	9
742	Wilson Cusack	2	🥈 star	dune	2024-09-25 11:22:50.782	9
20910	Zora	2	🥈 star	dune	2024-09-25 11:22:50.782	9
349775	Johnny Trend	2	🥈 star	dune	2024-09-25 11:22:50.782	9
15789	Sean Mundy 🎩🔥	2	🥈 star	dune	2024-09-25 11:22:50.782	9
431085	chinemelum	2	🥈 star	dune	2024-09-25 11:22:50.782	9
349331	Cantus 🎩🍖Ⓜ️🎭	2	🥈 star	dune	2024-09-25 11:22:50.782	9
444033	Nobody $NBD 🎩🍖Ⓜ️	2	🥈 star	dune	2024-09-25 11:22:50.782	9
11528	Jacob	4	💎 vip	dune	2024-09-25 11:22:50.782	9
9595	Ponder Surveys	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
15576	PERCS ☀️	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
193	derek	2	🥈 star	dune	2024-09-25 11:22:50.782	9
419388	Ykha Amelz	2	🥈 star	dune	2024-09-25 11:22:50.782	9
356241	Kevang30.degen.eth 🇻🇪	2	🥈 star	dune	2024-09-25 11:22:50.782	9
284063	Kyle B	2	🥈 star	dune	2024-09-25 11:22:50.782	9
243139	Blockhead	2	🥈 star	dune	2024-09-25 11:22:50.782	9
18203	Octant  ⧫	2	🥈 star	dune	2024-09-25 11:22:50.782	9
369	robin :•>	4	💎 vip	dune	2024-09-25 11:22:50.782	9
7933	Hades	4	💎 vip	dune	2024-09-25 11:22:50.782	9
276562	Ese 🌳	2	🥈 star	dune	2024-09-25 11:22:50.782	9
422367	ch0p🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
337511	CARDELUCCI🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
16565	OⓂ️id 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
309638	Alex	2	🥈 star	dune	2024-09-25 11:22:50.782	9
420930	Alistar☄️	2	🥈 star	dune	2024-09-25 11:22:50.782	9
6945	Alex A.🦊🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
516028	chii-ka!	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
1020	JAKE	2	🥈 star	dune	2024-09-25 11:22:50.782	9
198629	Matt 🎩🍖🎭	2	🥈 star	dune	2024-09-25 11:22:50.782	9
236391	TORMENTIAL 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
323251	Miguelgarest 	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
299853	base	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
397691	ronan.degen.eth🎩✨🍖	2	🥈 star	dune	2024-09-25 11:22:50.782	9
302642	Rose 🌸🧚‍♀️💎	2	🥈 star	dune	2024-09-25 11:22:50.782	9
403398	1000Words🪂 📷 🧗‍♂️	2	🥈 star	dune	2024-09-25 11:22:50.782	9
214841	Maurice	2	🥈 star	dune	2024-09-25 11:22:50.782	9
10144	johann	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
6801	julien	2	🥈 star	dune	2024-09-25 11:22:50.782	9
204173	Alex	2	🥈 star	dune	2024-09-25 11:22:50.782	9
335503	By Stani	2	🥈 star	dune	2024-09-25 11:22:50.782	9
317501	Rosstintexas 🎩 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
5781	prego	2	🥈 star	dune	2024-09-25 11:22:50.782	9
12778	big tone 🎩🧾	2	🥈 star	dune	2024-09-25 11:22:50.782	9
8405	Sean Wince 🎩🐹🟢↑	2	🥈 star	dune	2024-09-25 11:22:50.782	9
256500	Pain🖤🌹	2	🥈 star	dune	2024-09-25 11:22:50.782	9
626	Carlos Matallín	2	🥈 star	dune	2024-09-25 11:22:50.782	9
8476	SAINTLESS	2	🥈 star	dune	2024-09-25 11:22:50.782	9
365209	Mary Ann Artz 🎩🍔🍖🔲	2	🥈 star	dune	2024-09-25 11:22:50.782	9
293760	Jason🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
217834	Luka →{protocell:labs}← 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
13610	Leo 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
243818	meta-david🎩 | Building Scoop3	2	🥈 star	dune	2024-09-25 11:22:50.782	9
307224	Paul Prudence	2	🥈 star	dune	2024-09-25 11:22:50.782	9
235512	₲rava฿oy 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
409931	Alien Honey👽🖤	2	🥈 star	dune	2024-09-25 11:22:50.782	9
13121	LGHT 	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
232704	Pixel Symphony 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
228837	Flora Márquez 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
420493	Melanin💜✨	2	🥈 star	dune	2024-09-25 11:22:50.782	9
2433	seneca	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
281290	Ryan 🎩↑Ⓜ️🔵	2	🥈 star	dune	2024-09-25 11:22:50.782	9
10655	‍	2	🥈 star	dune	2024-09-25 11:22:50.782	9
7806	Saska from Phaver 🦄	2	🥈 star	dune	2024-09-25 11:22:50.782	9
419273	BoneScruffy	2	🥈 star	dune	2024-09-25 11:22:50.782	9
426	Brian Kim	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
3372	Eitzi 🎩 ⌐🆇-🆇 🌎-‘	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
342667	canek zapata	2	🥈 star	dune	2024-09-25 11:22:50.782	9
6400	Aspyn	2	🥈 star	dune	2024-09-25 11:22:50.782	9
250874	meguce	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
320215	𝖉𝖞𝖈𝖕¹ᵍ💋	2	🥈 star	dune	2024-09-25 11:22:50.782	9
473065	WetSocks💦🧦	2	🥈 star	dune	2024-09-25 11:22:50.782	9
283441	Joely 🎩🏰	2	🥈 star	dune	2024-09-25 11:22:50.782	9
414004	diVOn 🩶Ⓜ️🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
12915	0xJudd.eth 🎩↑	2	🥈 star	dune	2024-09-25 11:22:50.782	9
466688	Tim	2	🥈 star	dune	2024-09-25 11:22:50.782	9
490475	mozzigom🦜🎩👏	2	🥈 star	dune	2024-09-25 11:22:50.782	9
336567	Tater 🥔Ⓜ️	2	🥈 star	dune	2024-09-25 11:22:50.782	9
8	jacob	4	💎 vip	dune	2024-09-25 11:22:50.782	9
6841	Tony D’Addeo 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
3304	casslin.eth	2	🥈 star	dune	2024-09-25 11:22:50.782	9
242052	𝐚𝐦𝐛𝐞𝐫 ✷ 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
437559	Yaoyoros	2	🥈 star	dune	2024-09-25 11:22:50.782	9
56	✳️ dcposch on daimo	4	💎 vip	dune	2024-09-25 11:22:50.782	9
347364	kurita🇯🇵🎩🍖🔵✨	2	🥈 star	dune	2024-09-25 11:22:50.782	9
200375	adnum	2	🥈 star	dune	2024-09-25 11:22:50.782	9
380455	Juliito.eth 🎩🍖🎭	2	🥈 star	dune	2024-09-25 11:22:50.782	9
3189	kingd.eth	2	🥈 star	dune	2024-09-25 11:22:50.782	9
308587	YEDAI 🐟 De-Jen 🎩🎭	2	🥈 star	dune	2024-09-25 11:22:50.782	9
8035	Joonatan | Phaver CEO	2	🥈 star	dune	2024-09-25 11:22:50.782	9
4409	Pete Horne	2	🥈 star	dune	2024-09-25 11:22:50.782	9
461302	dd8🎩🎭	2	🥈 star	dune	2024-09-25 11:22:50.782	9
381665	Blank Embrace	2	🥈 star	dune	2024-09-25 11:22:50.782	9
13536	Ⓜ️4NU33⌐◨-◨🎩🟣	2	🥈 star	dune	2024-09-25 11:22:50.782	9
349228	Crezno 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
280002	The Myth 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
266053	Funut🎩🔵🍖🐹 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
3	dwr.eth	4	vip	Dune	2024-03-14 23:35:36.746696	1
5650	vitalik.eth	4	vip	Dune	2024-03-14 23:35:36.746696	1
99	jessepollak	4	vip	Dune	2024-03-14 23:35:36.746696	1
2	v	4	vip	Dune	2024-03-14 23:35:36.746696	1
347	greg	3	influencer	Dune	2024-03-14 23:35:36.746696	1
1325	cassie	3	influencer	Dune	2024-03-14 23:35:36.746696	1
129	phil	3	influencer	Dune	2024-03-14 23:35:36.746696	1
8	jacob	4	vip	Dune	2024-03-14 23:35:36.746696	1
206	coopahtroopa.eth	4	vip	Dune	2024-03-14 23:35:36.746696	1
2433	seneca	4	vip	Dune	2024-03-14 23:35:36.746696	1
534	mikedemarais.eth	3	influencer	Dune	2024-03-14 23:35:36.746696	1
3621	horsefacts.eth	3	influencer	Dune	2024-03-14 23:35:36.746696	1
576	nonlinear.eth	4	vip	Dune	2024-03-14 23:35:36.746696	1
239	ted	3	influencer	Dune	2024-03-14 23:35:36.746696	1
2689	binji.eth	4	vip	Dune	2024-03-14 23:35:36.746696	1
12	linda	3	influencer	Dune	2024-03-14 23:35:36.746696	1
1237	nicholas	3	influencer	Dune	2024-03-14 23:35:36.746696	1
124	giu	3	influencer	Dune	2024-03-14 23:35:36.746696	1
1317	0xdesigner	3	influencer	Dune	2024-03-14 23:35:36.746696	1
13833	kaloh	4	vip	Dune	2024-03-14 23:35:36.746696	1
617	cameron	4	vip	Dune	2024-03-14 23:35:36.746696	1
1287	july	4	vip	Dune	2024-03-14 23:35:36.746696	1
602	betashop.eth	3	influencer	Dune	2024-03-14 23:35:36.746696	1
528	0xen	4	vip	Dune	2024-03-14 23:35:36.746696	1
680	woj.eth	3	influencer	Dune	2024-03-14 23:35:36.746696	1
1356	farcasteradmin.eth	4	vip	Dune	2024-03-14 23:35:36.746696	1
4407	keccers.eth	3	influencer	Dune	2024-03-14 23:35:36.746696	1
358	corbin.eth	3	influencer	Dune	2024-03-14 23:35:36.746696	1
472	ccarella.eth	3	influencer	Dune	2024-03-14 23:35:36.746696	1
1214	df	3	influencer	Dune	2024-03-14 23:35:36.746696	1
12142	base	3	influencer	Dune	2024-03-14 23:35:36.746696	1
539	ace	3	influencer	Dune	2024-03-14 23:35:36.746696	1
8046	rsa.eth	3	influencer	Dune	2024-03-14 23:35:36.746696	1
3642	toadyhawk.eth	3	influencer	Dune	2024-03-14 23:35:36.746696	1
1110	perl	3	influencer	Dune	2024-03-14 23:35:36.746696	1
4036	sassal.eth	3	influencer	Dune	2024-03-14 23:35:36.746696	1
20919	rainbow	3	influencer	Dune	2024-03-14 23:35:36.746696	1
7251	ciniz	3	influencer	Dune	2024-03-14 23:35:36.746696	1
2904	wake	3	influencer	Dune	2024-03-14 23:35:36.746696	1
9595	survey	3	influencer	Dune	2024-03-14 23:35:36.746696	1
2252	sui	3	influencer	Dune	2024-03-14 23:35:36.746696	1
13121	lght.eth	3	influencer	Dune	2024-03-14 23:35:36.746696	1
2417	robrecht	3	influencer	Dune	2024-03-14 23:35:36.746696	1
9135	kugusha.eth	3	influencer	Dune	2024-03-14 23:35:36.746696	1
259196	farlaunch	3	influencer	Dune	2024-03-14 23:35:36.746696	1
329883	wowbase	3	influencer	Dune	2024-03-14 23:35:36.746696	1
5991	mxvoid	3	influencer	Dune	2024-03-14 23:35:36.746696	1
5431	esdotge.eth	3	influencer	Dune	2024-03-14 23:35:36.746696	1
10810	gami	3	influencer	Dune	2024-03-14 23:35:36.746696	1
1606	samantha	3	influencer	Dune	2024-03-14 23:35:36.746696	1
2007	jacopo.eth	3	influencer	Dune	2024-03-14 23:35:36.746696	1
1285	benersing	3	influencer	Dune	2024-03-14 23:35:36.746696	1
2163	cryptogirls	3	influencer	Dune	2024-03-14 23:35:36.746696	1
738	alexmasmej.eth	3	influencer	Dune	2024-03-14 23:35:36.746696	1
2210	kenny	3	influencer	Dune	2024-03-14 23:35:36.746696	1
339515	farcasterranking	3	influencer	Dune	2024-03-14 23:35:36.746696	1
7143	six	3	influencer	Dune	2024-03-14 23:35:36.746696	1
345923	farcastercoin	3	influencer	Dune	2024-03-14 23:35:36.746696	1
7637	aaronrferguson.eth	3	influencer	Dune	2024-03-14 23:35:36.746696	1
274138	farbase	3	influencer	Dune	2024-03-14 23:35:36.746696	1
8447	eriks	3	influencer	Dune	2024-03-14 23:35:36.746696	1
13505	j-valeska	3	influencer	Dune	2024-03-14 23:35:36.746696	1
15983	jacek	3	influencer	Dune	2024-03-14 23:35:36.746696	1
24005	rarible	3	influencer	Dune	2024-03-14 23:35:36.746696	1
7620	cybershakti	3	influencer	Dune	2024-03-14 23:35:36.746696	1
4482	deployer	3	influencer	Dune	2024-03-14 23:35:36.746696	1
361319	simson	3	influencer	Dune	2024-03-14 23:35:36.746696	1
10636	jam	3	influencer	Dune	2024-03-14 23:35:36.746696	1
3362	maschka	3	influencer	Dune	2024-03-14 23:35:36.746696	1
18085	mleejr	3	influencer	Dune	2024-03-14 23:35:36.746696	1
355066	mxchaosm	3	influencer	Dune	2024-03-14 23:35:36.746696	1
8685	markcarey	3	influencer	Dune	2024-03-14 23:35:36.746696	1
281289	tocd	3	influencer	Dune	2024-03-14 23:35:36.746696	1
3	dwr.eth	4	vip	Dune	2024-03-14 23:35:36.746696	3
5650	vitalik.eth	4	vip	Dune	2024-03-14 23:35:36.746696	3
99	jessepollak	4	vip	Dune	2024-03-14 23:35:36.746696	3
2	v	4	vip	Dune	2024-03-14 23:35:36.746696	3
347	greg	3	influencer	Dune	2024-03-14 23:35:36.746696	3
1325	cassie	3	influencer	Dune	2024-03-14 23:35:36.746696	3
129	phil	3	influencer	Dune	2024-03-14 23:35:36.746696	3
8	jacob	4	vip	Dune	2024-03-14 23:35:36.746696	3
206	coopahtroopa.eth	4	vip	Dune	2024-03-14 23:35:36.746696	3
2433	seneca	4	vip	Dune	2024-03-14 23:35:36.746696	3
534	mikedemarais.eth	3	influencer	Dune	2024-03-14 23:35:36.746696	3
3621	horsefacts.eth	3	influencer	Dune	2024-03-14 23:35:36.746696	3
576	nonlinear.eth	4	vip	Dune	2024-03-14 23:35:36.746696	3
239	ted	3	influencer	Dune	2024-03-14 23:35:36.746696	3
2689	binji.eth	4	vip	Dune	2024-03-14 23:35:36.746696	3
12	linda	3	influencer	Dune	2024-03-14 23:35:36.746696	3
1237	nicholas	3	influencer	Dune	2024-03-14 23:35:36.746696	3
124	giu	3	influencer	Dune	2024-03-14 23:35:36.746696	3
1317	0xdesigner	3	influencer	Dune	2024-03-14 23:35:36.746696	3
13833	kaloh	4	vip	Dune	2024-03-14 23:35:36.746696	3
617	cameron	4	vip	Dune	2024-03-14 23:35:36.746696	3
1287	july	4	vip	Dune	2024-03-14 23:35:36.746696	3
602	betashop.eth	3	influencer	Dune	2024-03-14 23:35:36.746696	3
528	0xen	4	vip	Dune	2024-03-14 23:35:36.746696	3
680	woj.eth	3	influencer	Dune	2024-03-14 23:35:36.746696	3
1356	farcasteradmin.eth	4	vip	Dune	2024-03-14 23:35:36.746696	3
4407	keccers.eth	3	influencer	Dune	2024-03-14 23:35:36.746696	3
358	corbin.eth	3	influencer	Dune	2024-03-14 23:35:36.746696	3
472	ccarella.eth	3	influencer	Dune	2024-03-14 23:35:36.746696	3
1214	df	3	influencer	Dune	2024-03-14 23:35:36.746696	3
12142	base	3	influencer	Dune	2024-03-14 23:35:36.746696	3
539	ace	3	influencer	Dune	2024-03-14 23:35:36.746696	3
8046	rsa.eth	3	influencer	Dune	2024-03-14 23:35:36.746696	3
3642	toadyhawk.eth	3	influencer	Dune	2024-03-14 23:35:36.746696	3
1110	perl	3	influencer	Dune	2024-03-14 23:35:36.746696	3
4036	sassal.eth	3	influencer	Dune	2024-03-14 23:35:36.746696	3
20919	rainbow	3	influencer	Dune	2024-03-14 23:35:36.746696	3
7251	ciniz	3	influencer	Dune	2024-03-14 23:35:36.746696	3
2904	wake	3	influencer	Dune	2024-03-14 23:35:36.746696	3
9595	survey	3	influencer	Dune	2024-03-14 23:35:36.746696	3
2252	sui	3	influencer	Dune	2024-03-14 23:35:36.746696	3
13121	lght.eth	3	influencer	Dune	2024-03-14 23:35:36.746696	3
2417	robrecht	3	influencer	Dune	2024-03-14 23:35:36.746696	3
9135	kugusha.eth	3	influencer	Dune	2024-03-14 23:35:36.746696	3
259196	farlaunch	3	influencer	Dune	2024-03-14 23:35:36.746696	3
329883	wowbase	3	influencer	Dune	2024-03-14 23:35:36.746696	3
5991	mxvoid	3	influencer	Dune	2024-03-14 23:35:36.746696	3
5431	esdotge.eth	3	influencer	Dune	2024-03-14 23:35:36.746696	3
10810	gami	3	influencer	Dune	2024-03-14 23:35:36.746696	3
1606	samantha	3	influencer	Dune	2024-03-14 23:35:36.746696	3
2007	jacopo.eth	3	influencer	Dune	2024-03-14 23:35:36.746696	3
1285	benersing	3	influencer	Dune	2024-03-14 23:35:36.746696	3
2163	cryptogirls	3	influencer	Dune	2024-03-14 23:35:36.746696	3
738	alexmasmej.eth	3	influencer	Dune	2024-03-14 23:35:36.746696	3
2210	kenny	3	influencer	Dune	2024-03-14 23:35:36.746696	3
339515	farcasterranking	3	influencer	Dune	2024-03-14 23:35:36.746696	3
7143	six	3	influencer	Dune	2024-03-14 23:35:36.746696	3
345923	farcastercoin	3	influencer	Dune	2024-03-14 23:35:36.746696	3
7637	aaronrferguson.eth	3	influencer	Dune	2024-03-14 23:35:36.746696	3
274138	farbase	3	influencer	Dune	2024-03-14 23:35:36.746696	3
8447	eriks	3	influencer	Dune	2024-03-14 23:35:36.746696	3
13505	j-valeska	3	influencer	Dune	2024-03-14 23:35:36.746696	3
15983	jacek	3	influencer	Dune	2024-03-14 23:35:36.746696	3
24005	rarible	3	influencer	Dune	2024-03-14 23:35:36.746696	3
7620	cybershakti	3	influencer	Dune	2024-03-14 23:35:36.746696	3
4482	deployer	3	influencer	Dune	2024-03-14 23:35:36.746696	3
361319	simson	3	influencer	Dune	2024-03-14 23:35:36.746696	3
10636	jam	3	influencer	Dune	2024-03-14 23:35:36.746696	3
3362	maschka	3	influencer	Dune	2024-03-14 23:35:36.746696	3
18085	mleejr	3	influencer	Dune	2024-03-14 23:35:36.746696	3
355066	mxchaosm	3	influencer	Dune	2024-03-14 23:35:36.746696	3
8685	markcarey	3	influencer	Dune	2024-03-14 23:35:36.746696	3
281289	tocd	3	influencer	Dune	2024-03-14 23:35:36.746696	3
403517	lilly 🥀	2	🥈 star	dune	2024-09-25 11:22:50.782	9
8637	Shaya	2	🥈 star	dune	2024-09-25 11:22:50.782	9
259597	Aldi Russalam🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
478791	dabie.cast😸	2	🥈 star	dune	2024-09-25 11:22:50.782	9
368412	Mfer Ones 🎩🔵	2	🥈 star	dune	2024-09-25 11:22:50.782	9
380950	silly goose	2	🥈 star	dune	2024-09-25 11:22:50.782	9
508394	Dan	2	🥈 star	dune	2024-09-25 11:22:50.782	9
194	rish	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
12990	Juli 🎩↑	2	🥈 star	dune	2024-09-25 11:22:50.782	9
508409	Kiraa♡	2	🥈 star	dune	2024-09-25 11:22:50.782	9
291686	Tatiansa 🟪🟣. ⌐◨-◨	2	🥈 star	dune	2024-09-25 11:22:50.782	9
249122	Heather N. Stout 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
239	ted (not lasso)	4	💎 vip	dune	2024-09-25 11:22:50.782	9
4461	limone.eth	2	🥈 star	dune	2024-09-25 11:22:50.782	9
421661	Satoushi |SAT|	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
234568	Ventra.eth	2	🥈 star	dune	2024-09-25 11:22:50.782	9
318213	Lorna Mills🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
11632	Catwifhat🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
1606	Sam (crazy candle person) ✦ 	4	💎 vip	dune	2024-09-25 11:22:50.782	9
1171	𝚐𝔪𝟾𝚡𝚡𝟾	2	🥈 star	dune	2024-09-25 11:22:50.782	9
14364	Purp🇵🇸	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
292783	Travis LeRoy Southworth💎🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
1317	0xdesigner	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
4378	GIGAMΞSH	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
280	vrypan |--o--|	2	🥈 star	dune	2024-09-25 11:22:50.782	9
292506	Wellzy 🎩🏰🍖✞	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
8439	Eddie Wharton	2	🥈 star	dune	2024-09-25 11:22:50.782	9
2073	MOΞ	2	🥈 star	dune	2024-09-25 11:22:50.782	9
445127	yekta ✎	2	🥈 star	dune	2024-09-25 11:22:50.782	9
408746	NutellaCrepervert🎩🍖	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
7960	Sheldon Trotman	2	🥈 star	dune	2024-09-25 11:22:50.782	9
399883	Rundle 🧾🍖🎩➰	2	🥈 star	dune	2024-09-25 11:22:50.782	9
512534	Marwa 🔵🎩🍖	2	🥈 star	dune	2024-09-25 11:22:50.782	9
14988	milan.⌐◨-◨ 🔵🐹🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
5423	Paul Millerd	2	🥈 star	dune	2024-09-25 11:22:50.782	9
451	Michael Pfister	2	🥈 star	dune	2024-09-25 11:22:50.782	9
309043	Erik 	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
410492	Bstract	2	🥈 star	dune	2024-09-25 11:22:50.782	9
283144	Renée Campbell 🎩	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
441956	Arrotu	2	🥈 star	dune	2024-09-25 11:22:50.782	9
400028	Leo 🪴🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
379579	frodo.base.eth 🔵 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
267383	Seattledog🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
533	not parzival	4	💎 vip	dune	2024-09-25 11:22:50.782	9
8942	to	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
245124	frederick	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
11244	BFG 🎩↑🌱	2	🥈 star	dune	2024-09-25 11:22:50.782	9
10178	Hoot 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
263664	Oppai おっぱい 🍓	2	🥈 star	dune	2024-09-25 11:22:50.782	9
423036	Sheva	2	🥈 star	dune	2024-09-25 11:22:50.782	9
13803	indiorobot🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
4167	Nounish Prof ⌐◧-◧🎩	4	💎 vip	dune	2024-09-25 11:22:50.782	9
2588	Connor McCormick ☀️	2	🥈 star	dune	2024-09-25 11:22:50.782	9
271878	Metaphorical Leo	2	🥈 star	dune	2024-09-25 11:22:50.782	9
342717	Tamas Antal🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
17838	Lulu	2	🥈 star	dune	2024-09-25 11:22:50.782	9
8998	Anatcrypto 🏗️🎙️🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
308410	Manu Williams 🎩🔵💎	2	🥈 star	dune	2024-09-25 11:22:50.782	9
10095	SierraRenee Ayọ Ṣádé	2	🥈 star	dune	2024-09-25 11:22:50.782	9
9280	brennen	2	🥈 star	dune	2024-09-25 11:22:50.782	9
14369	madyak🔆🔵-'	2	🥈 star	dune	2024-09-25 11:22:50.782	9
14885	eirrann | he/him🎩🔵	2	🥈 star	dune	2024-09-25 11:22:50.782	9
9470	Sterling Schuyler	2	🥈 star	dune	2024-09-25 11:22:50.782	9
3850	ണ Ի ന ℇ ന ℇ ട	2	🥈 star	dune	2024-09-25 11:22:50.782	9
283	Jeff Feiwell 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
7637	aferg	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
20919	Rainbow	2	🥈 star	dune	2024-09-25 11:22:50.782	9
3842	Boys club	2	🥈 star	dune	2024-09-25 11:22:50.782	9
1024	cdt	2	🥈 star	dune	2024-09-25 11:22:50.782	9
204221	Jarrett	2	🥈 star	dune	2024-09-25 11:22:50.782	9
466312	whimsi	2	🥈 star	dune	2024-09-25 11:22:50.782	9
217780	Sujit 🇮🇳  🎩 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
510364	Duraa 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
310292	Gore.gif  🎩 Ⓜ️	2	🥈 star	dune	2024-09-25 11:22:50.782	9
13659	kevin j 🀙	2	🥈 star	dune	2024-09-25 11:22:50.782	9
422910	Ciberdelia	2	🥈 star	dune	2024-09-25 11:22:50.782	9
410577	Jessi ⌐◨-◨ 🤫🌭 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
499579	Chronist	2	🥈 star	dune	2024-09-25 11:22:50.782	9
12480	Thumbs Up	2	🥈 star	dune	2024-09-25 11:22:50.782	9
1303	charles (fka boop)	2	🥈 star	dune	2024-09-25 11:22:50.782	9
922	Max	2	🥈 star	dune	2024-09-25 11:22:50.782	9
228795	ViHa	2	🥈 star	dune	2024-09-25 11:22:50.782	9
449264	Caira.degen.eth🎩🎭ツ	2	🥈 star	dune	2024-09-25 11:22:50.782	9
410690	F. Dilek Yurdakul	2	🥈 star	dune	2024-09-25 11:22:50.782	9
386712	michelle thompson	2	🥈 star	dune	2024-09-25 11:22:50.782	9
590111	れじぇんどりゃー	2	🥈 star	dune	2024-09-25 11:22:50.782	9
1689	Stephan	4	💎 vip	dune	2024-09-25 11:22:50.782	9
249958	rickacrane  🎩Ⓜ️🎭 	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
318589	cap'n	2	🥈 star	dune	2024-09-25 11:22:50.782	9
420554	DegenDog🎩🔵🍄🎭Ⓜ️	2	🥈 star	dune	2024-09-25 11:22:50.782	9
746	cody	2	🥈 star	dune	2024-09-25 11:22:50.782	9
2883	Caden	2	🥈 star	dune	2024-09-25 11:22:50.782	9
381093	Ake - heyake.degen.eth	2	🥈 star	dune	2024-09-25 11:22:50.782	9
391793	Rafaello.base.eth	2	🥈 star	dune	2024-09-25 11:22:50.782	9
256931	•Catch0x22•	2	🥈 star	dune	2024-09-25 11:22:50.782	9
15351	0ffline.xo🐘🌳	2	🥈 star	dune	2024-09-25 11:22:50.782	9
380136	Alexei 🍖 🎩🎭🍄	2	🥈 star	dune	2024-09-25 11:22:50.782	9
330083	Marcelo Terça-Nada 💎🎩✨	2	🥈 star	dune	2024-09-25 11:22:50.782	9
1082	Vinay Vasanji	2	🥈 star	dune	2024-09-25 11:22:50.782	9
10	Elad	2	🥈 star	dune	2024-09-25 11:22:50.782	9
367639	Abdullah	2	🥈 star	dune	2024-09-25 11:22:50.782	9
410761	Dumb designer	2	🥈 star	dune	2024-09-25 11:22:50.782	9
5062	Zach	2	🥈 star	dune	2024-09-25 11:22:50.782	9
443198	Neos	2	🥈 star	dune	2024-09-25 11:22:50.782	9
401491	Zo	2	🥈 star	dune	2024-09-25 11:22:50.782	9
416401	Scrodom✌🏻🎩 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
323433	Roman 🎤	2	🥈 star	dune	2024-09-25 11:22:50.782	9
5049	Jawa	2	🥈 star	dune	2024-09-25 11:22:50.782	9
459278	NIKOOTINEⓂ️🎯🎭⚡️	2	🥈 star	dune	2024-09-25 11:22:50.782	9
397815	RJ (replyor) 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
301385	wakkin	2	🥈 star	dune	2024-09-25 11:22:50.782	9
273708	siadude.degen 🎩 🎭 Ⓜ️	2	🥈 star	dune	2024-09-25 11:22:50.782	9
3307	mizu.base.eth 🐕	2	🥈 star	dune	2024-09-25 11:22:50.782	9
435510	Alina 🎩 🟣 🎭 :•>	2	🥈 star	dune	2024-09-25 11:22:50.782	9
427838	Taksh 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
266782	Atnsarts	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
324915	Purpleman 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
18224	WalletConnect Network	2	🥈 star	dune	2024-09-25 11:22:50.782	9
14882	Hopi🎩🍖🎭🔵Ⓜ️	2	🥈 star	dune	2024-09-25 11:22:50.782	9
394357	Marcela	2	🥈 star	dune	2024-09-25 11:22:50.782	9
382891	Hua 🤔	2	🥈 star	dune	2024-09-25 11:22:50.782	9
9548	FarcasterMarketing	2	🥈 star	dune	2024-09-25 11:22:50.782	9
318610	micsolana	2	🥈 star	dune	2024-09-25 11:22:50.782	9
261625	Bálint Popovits🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
238394	Toshi	2	🥈 star	dune	2024-09-25 11:22:50.782	9
265153	Samanta 🎩🔵 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
2455	notdevin 	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
1110	Perl	2	🥈 star	dune	2024-09-25 11:22:50.782	9
337090	Brandon Yoshizawa 🎩🔵💎	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
466111	SVVVG3	2	🥈 star	dune	2024-09-25 11:22:50.782	9
8438	Toasterboyz	2	🥈 star	dune	2024-09-25 11:22:50.782	9
2194	Paul Cowgill	2	🥈 star	dune	2024-09-25 11:22:50.782	9
307568	111𐐉 K S 🌒 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
511479	Ruhul	2	🥈 star	dune	2024-09-25 11:22:50.782	9
457	Zach	2	🥈 star	dune	2024-09-25 11:22:50.782	9
535389	XBorn ID	2	🥈 star	dune	2024-09-25 11:22:50.782	9
344899	Gnosis Pay	2	🥈 star	dune	2024-09-25 11:22:50.782	9
616	dylan	2	🥈 star	dune	2024-09-25 11:22:50.782	9
4256	Mark Fishman	2	🥈 star	dune	2024-09-25 11:22:50.782	9
302556	Mikko 	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
229621	Ridham🎩Ⓜ️	2	🥈 star	dune	2024-09-25 11:22:50.782	9
283222	Aoife O’Dwyer ↑ ✈️ 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
14396	Rachel Wilkins 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
249232	Jotta.rs🍭🎩🎭	2	🥈 star	dune	2024-09-25 11:22:50.782	9
377111	RogueHax 🎩🎯	2	🥈 star	dune	2024-09-25 11:22:50.782	9
398028	Kat 🎩🔥	2	🥈 star	dune	2024-09-25 11:22:50.782	9
4044	alec.eth is yapping🤠	2	🥈 star	dune	2024-09-25 11:22:50.782	9
1114	Michael Silberling	2	🥈 star	dune	2024-09-25 11:22:50.782	9
7237	Thomas	4	💎 vip	dune	2024-09-25 11:22:50.782	9
322662	Yumemaboroshi 🫂 🍖🔮🍡	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
199989	Dani  ⌐◨-◨	2	🥈 star	dune	2024-09-25 11:22:50.782	9
196957	max ↑🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
4549	CryptoPlaza 🟣🎩Ⓜ️ OG449	2	🥈 star	dune	2024-09-25 11:22:50.782	9
360600	Esra Eslen	2	🥈 star	dune	2024-09-25 11:22:50.782	9
343855	darcris	2	🥈 star	dune	2024-09-25 11:22:50.782	9
1301	krel	2	🥈 star	dune	2024-09-25 11:22:50.782	9
238	hyperbad	2	🥈 star	dune	2024-09-25 11:22:50.782	9
527771	🐐559🎩⌐◨-◨🇲🇽	2	🥈 star	dune	2024-09-25 11:22:50.782	9
431	↑ j4ck 🥶 icebreaker.xyz ↑	4	💎 vip	dune	2024-09-25 11:22:50.782	9
7464	スピットファンク🍓	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
8433	CodinCowboy 🍖	2	🥈 star	dune	2024-09-25 11:22:50.782	9
20118	Stephen Miller 🍖⌐◨-◨	2	🥈 star	dune	2024-09-25 11:22:50.782	9
20402	Jeff Davis	2	🥈 star	dune	2024-09-25 11:22:50.782	9
247605	PermaNoob 🎩 🍖🌭🫂🧾	2	🥈 star	dune	2024-09-25 11:22:50.782	9
1285	Ben  🟪	2	🥈 star	dune	2024-09-25 11:22:50.782	9
3609	alixkun🎩🍡	2	🥈 star	dune	2024-09-25 11:22:50.782	9
19613	Fractal Visions🎩 ⌐◨-◨	2	🥈 star	dune	2024-09-25 11:22:50.782	9
5650	Vitalik Buterin	4	💎 vip	dune	2024-09-25 11:22:50.782	9
270684	ZafGod 🎩 	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
1992	Thibauld	2	🥈 star	dune	2024-09-25 11:22:50.782	9
192373	Leshka [MEME IN BIO] 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
6023	Steve	2	🥈 star	dune	2024-09-25 11:22:50.782	9
227242	helladj™	2	🥈 star	dune	2024-09-25 11:22:50.782	9
11760	 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
431233	Latuns.degen 🎭 🧾	2	🥈 star	dune	2024-09-25 11:22:50.782	9
291302	ajrony.base.eth 🔵	2	🥈 star	dune	2024-09-25 11:22:50.782	9
4327	Colin Johnson 💭	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
307736	General Ism 🎩Ⓜ️🤫	2	🥈 star	dune	2024-09-25 11:22:50.782	9
1656	Dan | Icebreaker	2	🥈 star	dune	2024-09-25 11:22:50.782	9
213263	tom.framedl.eth 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
423235	Bvst 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
408979	riya 🎩🍖Ⓜ️😹	2	🥈 star	dune	2024-09-25 11:22:50.782	9
279477	amc	2	🥈 star	dune	2024-09-25 11:22:50.782	9
300898	Optimism	2	🥈 star	dune	2024-09-25 11:22:50.782	9
10799	LEA 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
331067	Shibuya	2	🥈 star	dune	2024-09-25 11:22:50.782	9
8939	annelisa.eth	2	🥈 star	dune	2024-09-25 11:22:50.782	9
428931	Ritika	2	🥈 star	dune	2024-09-25 11:22:50.782	9
326306	Bren	2	🥈 star	dune	2024-09-25 11:22:50.782	9
415368	Saxophone🎩🍖	2	🥈 star	dune	2024-09-25 11:22:50.782	9
374339	Carla Monni	2	🥈 star	dune	2024-09-25 11:22:50.782	9
17064	standpoint.degen.eth 🎩 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
263619	0xvvp 🎩🧾	2	🥈 star	dune	2024-09-25 11:22:50.782	9
1214	David Furlong	2	🥈 star	dune	2024-09-25 11:22:50.782	9
262938	animated ➰🍖	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
368021	dopeboy.eth	2	🥈 star	dune	2024-09-25 11:22:50.782	9
375536	J Finn 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
210648	sweetman	2	🥈 star	dune	2024-09-25 11:22:50.782	9
382890	qabqabqab	2	🥈 star	dune	2024-09-25 11:22:50.782	9
210628	Ethan666.eth🎩🍖🔵🧾🟣	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
323070	Mahesh 🦉🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
318447	Plants 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
246905	Diji 🦉🎩 🔵 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
312	Les Greys	2	🥈 star	dune	2024-09-25 11:22:50.782	9
436577	kevin mfer 🎩	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
8152	 	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
4027	Rakshita Philip	2	🥈 star	dune	2024-09-25 11:22:50.782	9
369904	Cool Beans 🌞	2	🥈 star	dune	2024-09-25 11:22:50.782	9
482872	Niloofar 🪷	2	🥈 star	dune	2024-09-25 11:22:50.782	9
585995	Luca1111🔵 🔴	2	🥈 star	dune	2024-09-25 11:22:50.782	9
350911	compusophy	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
234796	jitz.base.eth	2	🥈 star	dune	2024-09-25 11:22:50.782	9
13323	Speakup 🎩🔮 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
419852	Jeroen Verhulst	2	🥈 star	dune	2024-09-25 11:22:50.782	9
8004	justin.framedl.eth	4	💎 vip	dune	2024-09-25 11:22:50.782	9
395346	Lambchop 🐺★ 	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
15821	IamWessel😶‍🌫️🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
353603	yusukerino	2	🥈 star	dune	2024-09-25 11:22:50.782	9
203666	Leovido 🎩Ⓜ️🌱	2	🥈 star	dune	2024-09-25 11:22:50.782	9
143	mk	2	🥈 star	dune	2024-09-25 11:22:50.782	9
263333	colfax	2	🥈 star	dune	2024-09-25 11:22:50.782	9
72	Garry Tan	2	🥈 star	dune	2024-09-25 11:22:50.782	9
437433	samvox	2	🥈 star	dune	2024-09-25 11:22:50.782	9
355351	7Parsnips 🍓🍖👀	2	🥈 star	dune	2024-09-25 11:22:50.782	9
460847	Sheena	2	🥈 star	dune	2024-09-25 11:22:50.782	9
188169	PΣDЯ0̷Ӿ.degen 🐹 🎩 💀	2	🥈 star	dune	2024-09-25 11:22:50.782	9
405941	nkemjika.eth	2	🥈 star	dune	2024-09-25 11:22:50.782	9
273379	elbi	2	🥈 star	dune	2024-09-25 11:22:50.782	9
346320	Qubyt 🎭	2	🥈 star	dune	2024-09-25 11:22:50.782	9
16636	LifeWithArt 💎	2	🥈 star	dune	2024-09-25 11:22:50.782	9
4271	LΞO 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
5620	welter	2	🥈 star	dune	2024-09-25 11:22:50.782	9
4163	KMac🍌 ⏩	4	💎 vip	dune	2024-09-25 11:22:50.782	9
301144	itslemon.eth	2	🥈 star	dune	2024-09-25 11:22:50.782	9
645771	Rodeo	2	🥈 star	dune	2024-09-25 11:22:50.782	9
321551	Tù.úk’z	2	🥈 star	dune	2024-09-25 11:22:50.782	9
4085	christopher	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
8685	Mark Carey 🎩🫂	2	🥈 star	dune	2024-09-25 11:22:50.782	9
412843	Rockruff🐶	2	🥈 star	dune	2024-09-25 11:22:50.782	9
2736	annoushka	2	🥈 star	dune	2024-09-25 11:22:50.782	9
296687	JC🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
299247	catswilleatyou🎩🎨	2	🥈 star	dune	2024-09-25 11:22:50.782	9
10215	zoo	2	🥈 star	dune	2024-09-25 11:22:50.782	9
502568	Dr blue lizardo	2	🥈 star	dune	2024-09-25 11:22:50.782	9
13948	Mazemari ☆	2	🥈 star	dune	2024-09-25 11:22:50.782	9
359	Nicholas Charriere	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
20384	basil ⚵	2	🥈 star	dune	2024-09-25 11:22:50.782	9
414955	Just Build	2	🥈 star	dune	2024-09-25 11:22:50.782	9
1068	pentacle	2	🥈 star	dune	2024-09-25 11:22:50.782	9
10694	Chukwuka Osakwe	2	🥈 star	dune	2024-09-25 11:22:50.782	9
1626	McBain 	4	💎 vip	dune	2024-09-25 11:22:50.782	9
5818	adrienne	4	💎 vip	dune	2024-09-25 11:22:50.782	9
57	packy 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
15513	HODLCEO	2	🥈 star	dune	2024-09-25 11:22:50.782	9
407655	Gil Tamin✨	2	🥈 star	dune	2024-09-25 11:22:50.782	9
269775	Guts 🧙‍♂️🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
354760	Adam	2	🥈 star	dune	2024-09-25 11:22:50.782	9
15069	Nadie ⌐◨-◨	2	🥈 star	dune	2024-09-25 11:22:50.782	9
510956	🅰️vel723Ⓜ️ 🎩🍖	2	🥈 star	dune	2024-09-25 11:22:50.782	9
475488	HankMoody 🎩 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
310145	audithor	2	🥈 star	dune	2024-09-25 11:22:50.782	9
2210	kenny 🎩	4	💎 vip	dune	2024-09-25 11:22:50.782	9
3417	BORED 🥱	2	🥈 star	dune	2024-09-25 11:22:50.782	9
2602	Ignas Peciura Ⓜ️	2	🥈 star	dune	2024-09-25 11:22:50.782	9
410789	Joe  🎩⏳ ⌐◨-◨	2	🥈 star	dune	2024-09-25 11:22:50.782	9
378	Colin	2	🥈 star	dune	2024-09-25 11:22:50.782	9
2689	binji 🔴	4	💎 vip	dune	2024-09-25 11:22:50.782	9
354795	aaron.degen.eth 🤡🍌🔲	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
248172	julierose	2	🥈 star	dune	2024-09-25 11:22:50.782	9
423378	David 🎩 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
196558	Jaadasss🙇‍♀️🐝	2	🥈 star	dune	2024-09-25 11:22:50.782	9
341438	hoshino🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
307899	Dehiscence 🔲	2	🥈 star	dune	2024-09-25 11:22:50.782	9
18763	↑🎩runn3rr 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
1725	Angel - Not A Bot	2	🥈 star	dune	2024-09-25 11:22:50.782	9
6473	albi is /nervous	2	🥈 star	dune	2024-09-25 11:22:50.782	9
13696	Pablofb	2	🥈 star	dune	2024-09-25 11:22:50.782	9
6731	Chicago 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
18471	P	2	🥈 star	dune	2024-09-25 11:22:50.782	9
349675	⌐◨-◨ 🔵 kinwiz.base.eth	2	🥈 star	dune	2024-09-25 11:22:50.782	9
4914	Kunal 👑🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
8949	🍅	2	🥈 star	dune	2024-09-25 11:22:50.782	9
3642	Toady Hawk 🟡🎩 ᖽ 	4	💎 vip	dune	2024-09-25 11:22:50.782	9
7061	Liang @ degencast.wtf 🎩 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
481970	Kat Kartel 🍖🃏🌈	2	🥈 star	dune	2024-09-25 11:22:50.782	9
322356	OhHungryArtist🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
2586	Ben Basche	2	🥈 star	dune	2024-09-25 11:22:50.782	9
20286	Ox Bid	2	🥈 star	dune	2024-09-25 11:22:50.782	9
274563	Giwa 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
4134	andrei	2	🥈 star	dune	2024-09-25 11:22:50.782	9
269405	PinstripedGator🐊🎩🍖🧾	2	🥈 star	dune	2024-09-25 11:22:50.782	9
197061	FabValle	2	🥈 star	dune	2024-09-25 11:22:50.782	9
2	Varun Srinivasan	4	💎 vip	dune	2024-09-25 11:22:50.782	9
60	Brenner	2	🥈 star	dune	2024-09-25 11:22:50.782	9
9856	0xLuo	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
2112	JB Rubinovitz ⌐◨-◨	2	🥈 star	dune	2024-09-25 11:22:50.782	9
310801	Never Famous Artists🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
351531	Joain🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
17316	mert	2	🥈 star	dune	2024-09-25 11:22:50.782	9
281676	Anemale🎩↑🔵	2	🥈 star	dune	2024-09-25 11:22:50.782	9
331908	AstroRoss 💎✨	2	🥈 star	dune	2024-09-25 11:22:50.782	9
296207	Jeff Mihaly  🎞🎼🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
346080	Valhalla 1 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
274580	SunnyDaye	2	🥈 star	dune	2024-09-25 11:22:50.782	9
21431	Gramajo👽	2	🥈 star	dune	2024-09-25 11:22:50.782	9
263821	Tim Smith 🎩🔵🐔	2	🥈 star	dune	2024-09-25 11:22:50.782	9
1918	𝚣𝚘𝚣 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
3306	Mantej Rajpal 🇺🇸 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
357745	Starboy 🎩✨	2	🥈 star	dune	2024-09-25 11:22:50.782	9
12738	m/branson	2	🥈 star	dune	2024-09-25 11:22:50.782	9
456735	hawaii	2	🥈 star	dune	2024-09-25 11:22:50.782	9
1970	grin↑	2	🥈 star	dune	2024-09-25 11:22:50.782	9
2211	Commstark 🎩🫂	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
411475	Haniz 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
409857	yerbearserker.base.eth 🧉🎯	2	🥈 star	dune	2024-09-25 11:22:50.782	9
409781	WAGMI 🎩😇	2	🥈 star	dune	2024-09-25 11:22:50.782	9
190218	Icetoad 🎩 🍕 🎶 🐈 💚	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
414258	lia🍅	2	🥈 star	dune	2024-09-25 11:22:50.782	9
308042	agathedavray	2	🥈 star	dune	2024-09-25 11:22:50.782	9
443825	meshki.framedl.eth	2	🥈 star	dune	2024-09-25 11:22:50.782	9
351897	Ramsey  🎩🤝 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
214569	LazyFrank🦉	2	🥈 star	dune	2024-09-25 11:22:50.782	9
212722	Uniswap Labs	2	🥈 star	dune	2024-09-25 11:22:50.782	9
432880	Francoise Gamma	2	🥈 star	dune	2024-09-25 11:22:50.782	9
12048	MattwithouttheT 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
3237	Nick T	2	🥈 star	dune	2024-09-25 11:22:50.782	9
18723	BrixBountyFarm 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
1349	avi	2	🥈 star	dune	2024-09-25 11:22:50.782	9
421924	0xcorgi 🧾	2	🥈 star	dune	2024-09-25 11:22:50.782	9
426065	Magda Americangangsta 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
456675	T A N V  I  R	2	🥈 star	dune	2024-09-25 11:22:50.782	9
7479	Jason	2	🥈 star	dune	2024-09-25 11:22:50.782	9
191593	. 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
7408	emush🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
417769	seanluke.eth	2	🥈 star	dune	2024-09-25 11:22:50.782	9
264612	Notorious $BIP	2	🥈 star	dune	2024-09-25 11:22:50.782	9
349599	Karmilla Shelly  🎩🔵	2	🥈 star	dune	2024-09-25 11:22:50.782	9
1237	nicholas 🧨 	4	💎 vip	dune	2024-09-25 11:22:50.782	9
4179	maurelian 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
2099	yuga.eth	2	🥈 star	dune	2024-09-25 11:22:50.782	9
291942	FREAK	2	🥈 star	dune	2024-09-25 11:22:50.782	9
12921	Je$$yFries 🙂‍↔️🍟💕	2	🥈 star	dune	2024-09-25 11:22:50.782	9
7910	Rch 🎩 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
485585	RAJUAN 🎩👑Ⓜ️	2	🥈 star	dune	2024-09-25 11:22:50.782	9
4612	sean 👤	2	🥈 star	dune	2024-09-25 11:22:50.782	9
243300	🌈 YON	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
445359	Mina 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
380660	Kyle B🍖🧾✨️🎭🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
440747	arob.base.eth🍖🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
375727	StudioRhijn 🍖🎩🐹🍡🦖	2	🥈 star	dune	2024-09-25 11:22:50.782	9
317528	Ben @ RSTLSS	2	🥈 star	dune	2024-09-25 11:22:50.782	9
211159	Ina	2	🥈 star	dune	2024-09-25 11:22:50.782	9
7992	Anna Morris 🎩🍿	2	🥈 star	dune	2024-09-25 11:22:50.782	9
16719	OG🏴‍☠️🔵🎩テ	2	🥈 star	dune	2024-09-25 11:22:50.782	9
423457	Ogerpon.framedl.eth	2	🥈 star	dune	2024-09-25 11:22:50.782	9
417299	Archit.base.eth 🦉🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
2526	Pratik	2	🥈 star	dune	2024-09-25 11:22:50.782	9
403020	Push 🎩🤌🏻	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
374498	Jon Perkins	2	🥈 star	dune	2024-09-25 11:22:50.782	9
234327	treeskulltown 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
1321	kepano	2	🥈 star	dune	2024-09-25 11:22:50.782	9
1841	martin ↑	2	🥈 star	dune	2024-09-25 11:22:50.782	9
330807	FEELS	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
12938	ash	2	🥈 star	dune	2024-09-25 11:22:50.782	9
358	Corbin Page	2	🥈 star	dune	2024-09-25 11:22:50.782	9
4923	antimo 🎩	4	💎 vip	dune	2024-09-25 11:22:50.782	9
434908	DegenPad🎩🐹	2	🥈 star	dune	2024-09-25 11:22:50.782	9
315676	Xose 🎩 🔵	2	🥈 star	dune	2024-09-25 11:22:50.782	9
17510	yu-san🎩🍖	2	🥈 star	dune	2024-09-25 11:22:50.782	9
8059	Natrix ֍ 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
482953	Kelvin🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
472	ccarella	4	💎 vip	dune	2024-09-25 11:22:50.782	9
15850	christin	4	💎 vip	dune	2024-09-25 11:22:50.782	9
7418	FlexasaurusRex◨-◨Ⓜ️🎩	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
19129	Sinaver	2	🥈 star	dune	2024-09-25 11:22:50.782	9
360601	Loudman.⌐◨-◨ 🏴‍☠️	2	🥈 star	dune	2024-09-25 11:22:50.782	9
195117	Jacque(she|her).⌐◨-◨	2	🥈 star	dune	2024-09-25 11:22:50.782	9
409	Div 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
466926	Perry🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
318162	Dalek🎩💜	2	🥈 star	dune	2024-09-25 11:22:50.782	9
12725	Leyla 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
665530	Freytrades🎩📈	2	🥈 star	dune	2024-09-25 11:22:50.782	9
379581	BanthaFodderDan	2	🥈 star	dune	2024-09-25 11:22:50.782	9
414383	Gabriel Nebular	2	🥈 star	dune	2024-09-25 11:22:50.782	9
211205	Aerodrome	2	🥈 star	dune	2024-09-25 11:22:50.782	9
3017	Rafi	2	🥈 star	dune	2024-09-25 11:22:50.782	9
4567	Symbiotech⌐◨-◨🟡🎩テ	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
265048	Monika 🎩🔵	2	🥈 star	dune	2024-09-25 11:22:50.782	9
5604	🚂	2	🥈 star	dune	2024-09-25 11:22:50.782	9
7791	karan 👑	2	🥈 star	dune	2024-09-25 11:22:50.782	9
4215	simon	2	🥈 star	dune	2024-09-25 11:22:50.782	9
6591	Matt Lee 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
5406	bradq  	2	🥈 star	dune	2024-09-25 11:22:50.782	9
12626	Lauren McDonagh-Pereira 	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
391861	activis.eth🎩 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
7692	Pierre Pauze 🔵 🚽	2	🥈 star	dune	2024-09-25 11:22:50.782	9
14447	Carlos28355.art 🎩🍖Ⓜ️	2	🥈 star	dune	2024-09-25 11:22:50.782	9
499373	WooDee 🎩🍖🧾Ⓜ️	2	🥈 star	dune	2024-09-25 11:22:50.782	9
510330	22	2	🥈 star	dune	2024-09-25 11:22:50.782	9
534	mike rainbow (rainbow mike) ↑	4	💎 vip	dune	2024-09-25 11:22:50.782	9
6806	dawufi	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
417554	onten.eth | Ⓜ️🍖🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
13797	Sato 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
5431	S·G 🎩↑◡̈	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
213144	Complexlity	2	🥈 star	dune	2024-09-25 11:22:50.782	9
282672	Alina	2	🥈 star	dune	2024-09-25 11:22:50.782	9
3895	drewcoffman	2	🥈 star	dune	2024-09-25 11:22:50.782	9
315256	GIG☀️	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
294226	Blackstock 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
1668	tomu	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
12400	ilannnnnnnnkatin	2	🥈 star	dune	2024-09-25 11:22:50.782	9
9055	Steen!!!	2	🥈 star	dune	2024-09-25 11:22:50.782	9
16176	miin	2	🥈 star	dune	2024-09-25 11:22:50.782	9
346798	Nacho 🍓🦍	2	🥈 star	dune	2024-09-25 11:22:50.782	9
270005	VIPER	2	🥈 star	dune	2024-09-25 11:22:50.782	9
460287	Floaty Bot	2	🥈 star	dune	2024-09-25 11:22:50.782	9
238829	Brynn Alise 🎩🔵	2	🥈 star	dune	2024-09-25 11:22:50.782	9
5583	Eric P. Rhodes	2	🥈 star	dune	2024-09-25 11:22:50.782	9
11681	Ajit Tripathi	2	🥈 star	dune	2024-09-25 11:22:50.782	9
7048	agoston nagy	2	🥈 star	dune	2024-09-25 11:22:50.782	9
2745	Steve	4	💎 vip	dune	2024-09-25 11:22:50.782	9
221578	Apex777 🦖	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
758919	Murtaza Hussain	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
397392	Ako	2	🥈 star	dune	2024-09-25 11:22:50.782	9
784003	Ran Domero	2	🥈 star	dune	2024-09-25 11:22:50.782	9
3112	rileybeans	2	🥈 star	dune	2024-09-25 11:22:50.782	9
1979	coachcoale.eth 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
3103	Aunt HoⓂ️ie	2	🥈 star	dune	2024-09-25 11:22:50.782	9
16148	EulerLagrange.eth	4	💎 vip	dune	2024-09-25 11:22:50.782	9
2007	jacopo	2	🥈 star	dune	2024-09-25 11:22:50.782	9
13874	The Dude Bart🐘🌳 ⌐◨-◨	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
395131	Cristian 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
191503	arfonzo	2	🥈 star	dune	2024-09-25 11:22:50.782	9
435085	Riddick🎩🍖	2	🥈 star	dune	2024-09-25 11:22:50.782	9
7143	six	4	💎 vip	dune	2024-09-25 11:22:50.782	9
162	Kostas Christidis	2	🥈 star	dune	2024-09-25 11:22:50.782	9
330133	Nathan A. Bauman	2	🥈 star	dune	2024-09-25 11:22:50.782	9
3621	horsefacts	4	💎 vip	dune	2024-09-25 11:22:50.782	9
51	Marc Andreessen	2	🥈 star	dune	2024-09-25 11:22:50.782	9
17356	muu	2	🥈 star	dune	2024-09-25 11:22:50.782	9
482024	Yavuz Sariyildiz	2	🥈 star	dune	2024-09-25 11:22:50.782	9
483365	not_not_Duna 🍖➰🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
260433	demang	2	🥈 star	dune	2024-09-25 11:22:50.782	9
18560	orCarlos - Noun 976	2	🥈 star	dune	2024-09-25 11:22:50.782	9
16214	Ayush Garg	2	🥈 star	dune	2024-09-25 11:22:50.782	9
4528	Spam Terrorist	2	🥈 star	dune	2024-09-25 11:22:50.782	9
386723	Mocha🎩🔵🎨	2	🥈 star	dune	2024-09-25 11:22:50.782	9
330471	Inna Mosina 🎩🔵💎	2	🥈 star	dune	2024-09-25 11:22:50.782	9
390829	🫧🎀gusanita	2	🥈 star	dune	2024-09-25 11:22:50.782	9
5328	CHIC	2	🥈 star	dune	2024-09-25 11:22:50.782	9
332316	Victor Esteves 🚁	2	🥈 star	dune	2024-09-25 11:22:50.782	9
371213	Dix 🎩 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
311387	NickyStixx.eth 🌭🎩🍖🎭	2	🥈 star	dune	2024-09-25 11:22:50.782	9
457716	AP 🥷	2	🥈 star	dune	2024-09-25 11:22:50.782	9
6373	priyanka 🦉	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
264222	dialethia 🍖🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
217248	Myk.eth	2	🥈 star	dune	2024-09-25 11:22:50.782	9
377	🦒	2	🥈 star	dune	2024-09-25 11:22:50.782	9
416094	MEK.txt	2	🥈 star	dune	2024-09-25 11:22:50.782	9
340560	Char🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
235323	antaur ↑	2	🥈 star	dune	2024-09-25 11:22:50.782	9
2252	Sui	2	🥈 star	dune	2024-09-25 11:22:50.782	9
435501	Diana 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
14199	æther	2	🥈 star	dune	2024-09-25 11:22:50.782	9
236812	Phaver 🦄	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
8106	Project7	2	🥈 star	dune	2024-09-25 11:22:50.782	9
435716	Majid	2	🥈 star	dune	2024-09-25 11:22:50.782	9
734400	Gwynne Michele	2	🥈 star	dune	2024-09-25 11:22:50.782	9
12335	Brais.eth	2	🥈 star	dune	2024-09-25 11:22:50.782	9
4606	Venkatesh Rao ☀️	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
421198	Negar Sepehr	2	🥈 star	dune	2024-09-25 11:22:50.782	9
368989	dante4ever.base.eth🏰🎯🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
9270	typo.eth	2	🥈 star	dune	2024-09-25 11:22:50.782	9
310928	Polymarket	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
8046	Ryan Sean Adams (rsa.eth)	2	🥈 star	dune	2024-09-25 11:22:50.782	9
419741	Abbas🎩👾	2	🥈 star	dune	2024-09-25 11:22:50.782	9
781098	microsub	2	🥈 star	dune	2024-09-25 11:22:50.782	9
393467	Cosmos Astro Art 💎🍖🎩✨	2	🥈 star	dune	2024-09-25 11:22:50.782	9
9218	tinyrainboot 🔮	2	🥈 star	dune	2024-09-25 11:22:50.782	9
5774	tldr (tim reilly)	4	💎 vip	dune	2024-09-25 11:22:50.782	9
269694	Bitfloorsghost	4	💎 vip	dune	2024-09-25 11:22:50.782	9
13596	hellno the optimist	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
6162	typeof.eth 🔵	2	🥈 star	dune	2024-09-25 11:22:50.782	9
309857	Coinbase Wallet	2	🥈 star	dune	2024-09-25 11:22:50.782	9
389456	borst ↑	2	🥈 star	dune	2024-09-25 11:22:50.782	9
261245	Erik Bulckens 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
236581	Cheryl 🔵	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
326433	Tmophoto 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
16567	Karo K	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
412772	Stay Pilled	2	🥈 star	dune	2024-09-25 11:22:50.782	9
13640	Hackware 🎩🧾	2	🥈 star	dune	2024-09-25 11:22:50.782	9
306610	FluffheadChaser	2	🥈 star	dune	2024-09-25 11:22:50.782	9
10810	gami ✨	2	🥈 star	dune	2024-09-25 11:22:50.782	9
306341	Rik Oostenbroek 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
373258	mass.framedl.eth	2	🥈 star	dune	2024-09-25 11:22:50.782	9
2441	grant 🌈 🎩 🐸	2	🥈 star	dune	2024-09-25 11:22:50.782	9
245579	sonny.base.eth🔵🎩Ⓜ️	2	🥈 star	dune	2024-09-25 11:22:50.782	9
493739	Agni	2	🥈 star	dune	2024-09-25 11:22:50.782	9
13418	David Tso (dave.base.eth) 🔵	2	🥈 star	dune	2024-09-25 11:22:50.782	9
124	Giuliano Giacaglia	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
2417	Rob Sanchez	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
321969	C O M P Ξ Z	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
20701	carlos	2	🥈 star	dune	2024-09-25 11:22:50.782	9
302400	Apollo 🎩🔵	2	🥈 star	dune	2024-09-25 11:22:50.782	9
509624	OTTI🎨🖌	2	🥈 star	dune	2024-09-25 11:22:50.782	9
417216	poyzn	2	🥈 star	dune	2024-09-25 11:22:50.782	9
66	Tayyab - d/acc	2	🥈 star	dune	2024-09-25 11:22:50.782	9
1430	wijuwiju.eth	2	🥈 star	dune	2024-09-25 11:22:50.782	9
3635	androidsixteen	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
478906	Jina	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
305843	Ashish	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
310953	nuel.	2	🥈 star	dune	2024-09-25 11:22:50.782	9
2600	depatchedmode	2	🥈 star	dune	2024-09-25 11:22:50.782	9
418671	Itsai ⌐◨-◨ 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
318473	pastel ← leo ꓽꓽ)	2	🥈 star	dune	2024-09-25 11:22:50.782	9
424658	Chanzy 🐣	2	🥈 star	dune	2024-09-25 11:22:50.782	9
246823	Haier (she) 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
364953	Shoaib🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
440524	Sina	2	🥈 star	dune	2024-09-25 11:22:50.782	9
3734	Sasquatch テ	2	🥈 star	dune	2024-09-25 11:22:50.782	9
2383	kaito	2	🥈 star	dune	2024-09-25 11:22:50.782	9
421001	Birtcorn $BRT	2	🥈 star	dune	2024-09-25 11:22:50.782	9
360623	Pelin Genç🩵🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
376224	Anna Zhukovska 🎩📷🔗	2	🥈 star	dune	2024-09-25 11:22:50.782	9
10971	Jared Hecht	2	🥈 star	dune	2024-09-25 11:22:50.782	9
313283	Luigi Stranieri	2	🥈 star	dune	2024-09-25 11:22:50.782	9
13577	PhiMarHal	2	🥈 star	dune	2024-09-25 11:22:50.782	9
248817	//Halo Machine//	2	🥈 star	dune	2024-09-25 11:22:50.782	9
53	Antonio García Martínez	2	🥈 star	dune	2024-09-25 11:22:50.782	9
382808	Cake One 🎩🔵🎭🔴	2	🥈 star	dune	2024-09-25 11:22:50.782	9
211535	Caygeon.degen.eth 🎩🏰🍖	2	🥈 star	dune	2024-09-25 11:22:50.782	9
10420	Lefteris Karapetsas	2	🥈 star	dune	2024-09-25 11:22:50.782	9
4753	Saumya Saxena 	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
318908	_ron_west_⚡power.degen.eth⚡	2	🥈 star	dune	2024-09-25 11:22:50.782	9
1766	Trent	2	🥈 star	dune	2024-09-25 11:22:50.782	9
285998	Hind🎩🔵	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
4383	LilPing	2	🥈 star	dune	2024-09-25 11:22:50.782	9
246448	Ethspresso 🚌🔵🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
316268	Bosque Gracias 🎩🎭	2	🥈 star	dune	2024-09-25 11:22:50.782	9
248226	y0b	2	🥈 star	dune	2024-09-25 11:22:50.782	9
20591	Kyle Tut	2	🥈 star	dune	2024-09-25 11:22:50.782	9
20005	Anaroth	2	🥈 star	dune	2024-09-25 11:22:50.782	9
3	Dan Romero	4	💎 vip	dune	2024-09-25 11:22:50.782	9
396484	👑eiteen go<3👒	2	🥈 star	dune	2024-09-25 11:22:50.782	9
326271	Tornado Rodriguez 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
236971	ruggy🧾🎩 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
420229	こじかちゃん (kozika)	2	🥈 star	dune	2024-09-25 11:22:50.782	9
680	​woj	4	💎 vip	dune	2024-09-25 11:22:50.782	9
1137	Poison Ivy	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
403090	Penguin	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
227886	Grit, إنشاءالله.eth	2	🥈 star	dune	2024-09-25 11:22:50.782	9
420540	Ox.crypto 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
200530	Salinek	2	🥈 star	dune	2024-09-25 11:22:50.782	9
355271	tape 🃏🍖	2	🥈 star	dune	2024-09-25 11:22:50.782	9
441632	Archilles ༄ 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
444929	Fredha.degen.eth 🎩Ⓜ️	2	🥈 star	dune	2024-09-25 11:22:50.782	9
3346	Haole	2	🥈 star	dune	2024-09-25 11:22:50.782	9
240835	kenanie.degen.eth	2	🥈 star	dune	2024-09-25 11:22:50.782	9
15983	Jacek.degen.eth 🎩	4	💎 vip	dune	2024-09-25 11:22:50.782	9
283597	Callum Wanderloots ✨	2	🥈 star	dune	2024-09-25 11:22:50.782	9
315697	Akinetic ⚔️	2	🥈 star	dune	2024-09-25 11:22:50.782	9
353819	jaguar.degen.eth🎩🍖🍡	2	🥈 star	dune	2024-09-25 11:22:50.782	9
485965	Milesx.degen.eth 🎯	2	🥈 star	dune	2024-09-25 11:22:50.782	9
15211	statuette.base.eth	2	🥈 star	dune	2024-09-25 11:22:50.782	9
462989	Reza 🍁📷	2	🥈 star	dune	2024-09-25 11:22:50.782	9
14127	BBB 👊	2	🥈 star	dune	2024-09-25 11:22:50.782	9
18570	daivd 🎩👽 ↑	2	🥈 star	dune	2024-09-25 11:22:50.782	9
12256	kia	2	🥈 star	dune	2024-09-25 11:22:50.782	9
279980	Globs🔵	2	🥈 star	dune	2024-09-25 11:22:50.782	9
392597	Tina	2	🥈 star	dune	2024-09-25 11:22:50.782	9
223778	Jerry-d 🍖👽🎩🎭↑	2	🥈 star	dune	2024-09-25 11:22:50.782	9
502908	Ibiwunmi 🎭🎩⚡🍄🔵🤡	2	🥈 star	dune	2024-09-25 11:22:50.782	9
352694	Casey Joiner	2	🥈 star	dune	2024-09-25 11:22:50.782	9
477126	Mika Doe	2	🥈 star	dune	2024-09-25 11:22:50.782	9
214598	thugkitten 🎩 🍖	2	🥈 star	dune	2024-09-25 11:22:50.782	9
39	Sam Iglesias	2	🥈 star	dune	2024-09-25 11:22:50.782	9
7951	aerique	2	🥈 star	dune	2024-09-25 11:22:50.782	9
411955	Rebin🔵🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
263339	Chris Follows 🎩💎✨	2	🥈 star	dune	2024-09-25 11:22:50.782	9
17979	Harpalsinh Jadeja	2	🥈 star	dune	2024-09-25 11:22:50.782	9
771	jp 🎩🚢	2	🥈 star	dune	2024-09-25 11:22:50.782	9
13495	Stefanie	2	🥈 star	dune	2024-09-25 11:22:50.782	9
349816	Maie 🎩🎭	2	🥈 star	dune	2024-09-25 11:22:50.782	9
420374	aydinmustafa.degen 🎩🔵✨	2	🥈 star	dune	2024-09-25 11:22:50.782	9
10066	Monica Talan 🌐 🍄🎭	2	🥈 star	dune	2024-09-25 11:22:50.782	9
399658	Bárbara Bezina	2	🥈 star	dune	2024-09-25 11:22:50.782	9
243294	Ξric Juta 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
325	Victor Ma 🧾	2	🥈 star	dune	2024-09-25 11:22:50.782	9
19832	TheModestThief🎩 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
417851	Tracyit 🍖🎩Ⓜ️	2	🥈 star	dune	2024-09-25 11:22:50.782	9
276	markus - ethOS - e/acc-d	2	🥈 star	dune	2024-09-25 11:22:50.782	9
250455	Olga	2	🥈 star	dune	2024-09-25 11:22:50.782	9
516505	Roni_travis🎭Ⓜ️🎩✨	2	🥈 star	dune	2024-09-25 11:22:50.782	9
631749	GINyO	2	🥈 star	dune	2024-09-25 11:22:50.782	9
224429	plastic 🎩👽	2	🥈 star	dune	2024-09-25 11:22:50.782	9
445793	Emp	2	🥈 star	dune	2024-09-25 11:22:50.782	9
1407	Zinger ↑ is job hunting	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
283056	Inceptionally 🎩  	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
13901	Marissa	2	🥈 star	dune	2024-09-25 11:22:50.782	9
348643	Petra ✨	2	🥈 star	dune	2024-09-25 11:22:50.782	9
440475	ItsNaastaaraan🔵Ⓜ️	2	🥈 star	dune	2024-09-25 11:22:50.782	9
511655	Bryhmo 🐭🎩🍖	2	🥈 star	dune	2024-09-25 11:22:50.782	9
14191	Dragic	2	🥈 star	dune	2024-09-25 11:22:50.782	9
307834	Trebor🎩🟡	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
249332	Alex Mack 🏔️	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
308045	Samir 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
308827	bluretina 🎩Ⓜ️	2	🥈 star	dune	2024-09-25 11:22:50.782	9
3174	𒐪	2	🥈 star	dune	2024-09-25 11:22:50.782	9
269321	Domino	2	🥈 star	dune	2024-09-25 11:22:50.782	9
349545	Fernando Fragoso	2	🥈 star	dune	2024-09-25 11:22:50.782	9
52	Sina Habibian	2	🥈 star	dune	2024-09-25 11:22:50.782	9
402888	Hnwcrypto 🎩🥭	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
340986	Trillobyte	2	🥈 star	dune	2024-09-25 11:22:50.782	9
338853	Jake 🌕	2	🥈 star	dune	2024-09-25 11:22:50.782	9
206	Coop	4	💎 vip	dune	2024-09-25 11:22:50.782	9
539	ace	4	💎 vip	dune	2024-09-25 11:22:50.782	9
8446	Filipe Macedo	2	🥈 star	dune	2024-09-25 11:22:50.782	9
527313	nounspaceTom.eth	2	🥈 star	dune	2024-09-25 11:22:50.782	9
390336	Kuntal Singhvi.eth 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
17690	Dracklyn.degen.eth 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
281836	dude 🧔🏻↑🔵🟣 	4	💎 vip	dune	2024-09-25 11:22:50.782	9
9318	catra ↑	2	🥈 star	dune	2024-09-25 11:22:50.782	9
406564	tomo🌏🇯🇵🎵🐹🦀🍓	2	🥈 star	dune	2024-09-25 11:22:50.782	9
201043	Losi 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
273442	Sam	2	🥈 star	dune	2024-09-25 11:22:50.782	9
193928	✿ Gil Alter ✿	2	🥈 star	dune	2024-09-25 11:22:50.782	9
1236	Syed Shah🏴‍☠️🌊	2	🥈 star	dune	2024-09-25 11:22:50.782	9
412	Joe Blau 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
780900	Naomi	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
196041	Suffuze 🎮➰🍖	2	🥈 star	dune	2024-09-25 11:22:50.782	9
435160	Abubakar🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
507309	Magia	2	🥈 star	dune	2024-09-25 11:22:50.782	9
516	itai (building dynamic.xyz)	2	🥈 star	dune	2024-09-25 11:22:50.782	9
451779	AlinaAlina🎩💙🎭💎	2	🥈 star	dune	2024-09-25 11:22:50.782	9
434822	Marina Ahmadova🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
385571	Hookage Ⓜ️ 🎩 Amuna  	2	🥈 star	dune	2024-09-25 11:22:50.782	9
241763	DePIN 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
324497	Fabiano Speziari 🎩💎	2	🥈 star	dune	2024-09-25 11:22:50.782	9
3305	Joan Westenberg	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
332502	Morbeck 💎	2	🥈 star	dune	2024-09-25 11:22:50.782	9
265108	OMGiDRAWEDit 🦎	2	🥈 star	dune	2024-09-25 11:22:50.782	9
278653	alexesc 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
679	Daniel Sinclair	2	🥈 star	dune	2024-09-25 11:22:50.782	9
5653	Sher Chaudhary	2	🥈 star	dune	2024-09-25 11:22:50.782	9
414259	earthcone	2	🥈 star	dune	2024-09-25 11:22:50.782	9
263574	TonyⓂ️inh🎩🍖✨🎭	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
317777	bigdegenenergy.eth Ⓜ️🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
243719	downshift	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
11782	Juan Antonio Lleó 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
209951	Swishh ↑	2	🥈 star	dune	2024-09-25 11:22:50.782	9
309567	Kristin Piljay 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
1887	Alberto Ornaghi	2	🥈 star	dune	2024-09-25 11:22:50.782	9
3206	YB	2	🥈 star	dune	2024-09-25 11:22:50.782	9
10174	Ray F. 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
12168	lawl	2	🥈 star	dune	2024-09-25 11:22:50.782	9
420880	Solidadeva 🎩🪄🔮	2	🥈 star	dune	2024-09-25 11:22:50.782	9
385469	HARIOLOGY 🎩Ⓜ️	2	🥈 star	dune	2024-09-25 11:22:50.782	9
5701	ChrisCoCreated	2	🥈 star	dune	2024-09-25 11:22:50.782	9
348814	BaseFrens Ⓜ️	2	🥈 star	dune	2024-09-25 11:22:50.782	9
19858	BorrowLucid 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
12142	Base	4	💎 vip	dune	2024-09-25 11:22:50.782	9
4564	kevin	2	🥈 star	dune	2024-09-25 11:22:50.782	9
565051	Moxie Protocol	2	🥈 star	dune	2024-09-25 11:22:50.782	9
363197	Baker Grace	2	🥈 star	dune	2024-09-25 11:22:50.782	9
344203	Danny	2	🥈 star	dune	2024-09-25 11:22:50.782	9
420304	Don 🎩💎	2	🥈 star	dune	2024-09-25 11:22:50.782	9
386444	Sappi⑅◡̈*	2	🥈 star	dune	2024-09-25 11:22:50.782	9
387202	Blue Cockatoo	2	🥈 star	dune	2024-09-25 11:22:50.782	9
535238	Anthony Pete🧾🎩🍖🎭🌳	2	🥈 star	dune	2024-09-25 11:22:50.782	9
277952	Dvyne	2	🥈 star	dune	2024-09-25 11:22:50.782	9
262566	Prosocialise Foundation🍄 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
453	Daniel Fernandes	2	🥈 star	dune	2024-09-25 11:22:50.782	9
20434	David 📷🐋🌊	2	🥈 star	dune	2024-09-25 11:22:50.782	9
432536	Tomba	2	🥈 star	dune	2024-09-25 11:22:50.782	9
99	jesse.base.eth 🔵	4	💎 vip	dune	2024-09-25 11:22:50.782	9
656	raz	2	🥈 star	dune	2024-09-25 11:22:50.782	9
7258	elle	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
245902	nattc.framedl.eth 🫂⚡️	2	🥈 star	dune	2024-09-25 11:22:50.782	9
471160	Panji 🟡	2	🥈 star	dune	2024-09-25 11:22:50.782	9
244479	Dragonite.eth 🎩🥇✍️🧾	2	🥈 star	dune	2024-09-25 11:22:50.782	9
169	fredwilson	4	💎 vip	dune	2024-09-25 11:22:50.782	9
15776	Claireujma 🎩🔵✨	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
326677	Luciana Guerra🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
8531	Dean Pierce 👨‍💻🌎🌍	2	🥈 star	dune	2024-09-25 11:22:50.782	9
461236	Maheenblues.base.eth	2	🥈 star	dune	2024-09-25 11:22:50.782	9
330172	BroekaselaluJp🎯Ⓜ️🎩🔵	2	🥈 star	dune	2024-09-25 11:22:50.782	9
4473	kayvon	2	🥈 star	dune	2024-09-25 11:22:50.782	9
13086	696🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
253127	agusti 🐘🔵	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
242661	puffdood	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
452094	Srivatsan sankaran 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
269091	ns	2	🥈 star	dune	2024-09-25 11:22:50.782	9
3652	aqueous 🎩🍖👑Ⓜ️	2	🥈 star	dune	2024-09-25 11:22:50.782	9
306416	guruguruhyena🐹🎩✈️	2	🥈 star	dune	2024-09-25 11:22:50.782	9
343324	MightyMoss 🎩🔵❇️	2	🥈 star	dune	2024-09-25 11:22:50.782	9
12	Linda Xie	4	💎 vip	dune	2024-09-25 11:22:50.782	9
350139	joshisdead.eth	2	🥈 star	dune	2024-09-25 11:22:50.782	9
318702	Setter 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
351598	🍅speakingtomato	2	🥈 star	dune	2024-09-25 11:22:50.782	9
364017	Guil 🐘 🎩  	2	🥈 star	dune	2024-09-25 11:22:50.782	9
14455	Murder 🏳️‍🌈	2	🥈 star	dune	2024-09-25 11:22:50.782	9
6730	Juampi  @/build 🫡	2	🥈 star	dune	2024-09-25 11:22:50.782	9
218454	g-Ⓜ️ac 🔵 🎩🍖🍓	2	🥈 star	dune	2024-09-25 11:22:50.782	9
5851	Michail / Opium Hum / Hyper Real	2	🥈 star	dune	2024-09-25 11:22:50.782	9
13314	origin⚡️	2	🥈 star	dune	2024-09-25 11:22:50.782	9
7715	Just Royal	2	🥈 star	dune	2024-09-25 11:22:50.782	9
294300	Sasha ⛓️🎩🔵 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
221519	0xZara.eth🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
473	Matthew	4	💎 vip	dune	2024-09-25 11:22:50.782	9
2480	humpty 	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
373025	Ateliê 407 🌈🎩Ⓜ️	2	🥈 star	dune	2024-09-25 11:22:50.782	9
306404	Harry	2	🥈 star	dune	2024-09-25 11:22:50.782	9
330738	Dipanjan Pal 🦉🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
446697	Zenigame	2	🥈 star	dune	2024-09-25 11:22:50.782	9
10705	Bård Ionson 🎩 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
14351	dev 👨🏻‍🌾Ⓜ️🎩	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
4294	tricil	2	🥈 star	dune	2024-09-25 11:22:50.782	9
417063	Breech 🎩🍖Ⓜ️	2	🥈 star	dune	2024-09-25 11:22:50.782	9
477292	Gambino	2	🥈 star	dune	2024-09-25 11:22:50.782	9
12756	Fer 🎩🖼️	2	🥈 star	dune	2024-09-25 11:22:50.782	9
399892	Ⓜ️elika  ⌐◨-◨🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
6596	kk	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
514366	Block.base.eth 🔵	2	🥈 star	dune	2024-09-25 11:22:50.782	9
265951	imp0ster	2	🥈 star	dune	2024-09-25 11:22:50.782	9
472352	Data Velvet 🎩💙	2	🥈 star	dune	2024-09-25 11:22:50.782	9
80	Liam	2	🥈 star	dune	2024-09-25 11:22:50.782	9
557899	Yoyo	2	🥈 star	dune	2024-09-25 11:22:50.782	9
211186	Ray  🎩 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
15997	Pauline Faieff 🦋	2	🥈 star	dune	2024-09-25 11:22:50.782	9
18048	Daria Klepikova	2	🥈 star	dune	2024-09-25 11:22:50.782	9
443	Jordan Kutzer	2	🥈 star	dune	2024-09-25 11:22:50.782	9
252500	mchx	2	🥈 star	dune	2024-09-25 11:22:50.782	9
6622	frdysk.framedl.eth	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
211272	DCinvestor	2	🥈 star	dune	2024-09-25 11:22:50.782	9
16405	charlie.base.eth	2	🥈 star	dune	2024-09-25 11:22:50.782	9
5694	shazow	2	🥈 star	dune	2024-09-25 11:22:50.782	9
14537	Mort Espiral 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
343971	chie lilybell	2	🥈 star	dune	2024-09-25 11:22:50.782	9
431880	basement5k.⌐◨-◨ 🟡 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
129	phil	4	💎 vip	dune	2024-09-25 11:22:50.782	9
297066	Supertaster.degen.eth 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
28	Alok Vasudev	2	🥈 star	dune	2024-09-25 11:22:50.782	9
7251	ciniz	4	💎 vip	dune	2024-09-25 11:22:50.782	9
385955	DegenFans 🎩🔵🫂Ⓜ️	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
2802	Garrett 	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
310124	eggman 🔵	2	🥈 star	dune	2024-09-25 11:22:50.782	9
2341	tani	2	🥈 star	dune	2024-09-25 11:22:50.782	9
415225	Shazam⚡️🧢🔵	2	🥈 star	dune	2024-09-25 11:22:50.782	9
8332	AJ	2	🥈 star	dune	2024-09-25 11:22:50.782	9
11158	Ringo🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
13505	J. Valeska 🦊🎩🫂 	4	💎 vip	dune	2024-09-25 11:22:50.782	9
2134	Kazi 	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
278406	Joelle LB 	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
408777	Angelus 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
323144	WOO🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
11004	Pornsoup 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
314532	H. C. Holter 😻👩‍🎨😈	2	🥈 star	dune	2024-09-25 11:22:50.782	9
373242	M░A░Z░i░N	2	🥈 star	dune	2024-09-25 11:22:50.782	9
235303	Merlin Egalite	2	🥈 star	dune	2024-09-25 11:22:50.782	9
426045	Ryan J. Shaw	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
768581	Tay Zonday	2	🥈 star	dune	2024-09-25 11:22:50.782	9
290	matticus.evav.eth ⌐◨-◨	2	🥈 star	dune	2024-09-25 11:22:50.782	9
13089	Arjan | That Poetry Guy	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
4534	Amadon	2	🥈 star	dune	2024-09-25 11:22:50.782	9
336022	degen chad 🎩🤫Ⓜ️	2	🥈 star	dune	2024-09-25 11:22:50.782	9
371561	Neil Burnell 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
12021	kbc	2	🥈 star	dune	2024-09-25 11:22:50.782	9
285462	non 🐹	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
467312	Your BooThang🩷🌷	2	🥈 star	dune	2024-09-25 11:22:50.782	9
309639	E R M A N ⚓	2	🥈 star	dune	2024-09-25 11:22:50.782	9
189874	Marc 🎩 🔵	2	🥈 star	dune	2024-09-25 11:22:50.782	9
602	Jason Goldberg Ⓜ️ 💜	4	💎 vip	dune	2024-09-25 11:22:50.782	9
17114	Matcha 🍵 ⌐◨-◨	2	🥈 star	dune	2024-09-25 11:22:50.782	9
210698	𝙗𝙡𝙖𝙣𝙠	2	🥈 star	dune	2024-09-25 11:22:50.782	9
240586	Goldy	2	🥈 star	dune	2024-09-25 11:22:50.782	9
379089	Asef	2	🥈 star	dune	2024-09-25 11:22:50.782	9
349621	Sky Goodman🎩🎭💎	2	🥈 star	dune	2024-09-25 11:22:50.782	9
197340	Taye 🎩🔵 👽⛏️	2	🥈 star	dune	2024-09-25 11:22:50.782	9
12156	Isa Rus 🎩💎	2	🥈 star	dune	2024-09-25 11:22:50.782	9
9326	Mike | Abundance	2	🥈 star	dune	2024-09-25 11:22:50.782	9
5179	jtgi - mostly offline 23 -> 05	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
767	Kabir 🔵	2	🥈 star	dune	2024-09-25 11:22:50.782	9
278239	Strano 👁️‍🗨️	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
403573	TeleD - Space Doctor	2	🥈 star	dune	2024-09-25 11:22:50.782	9
406908	no faith	2	🥈 star	dune	2024-09-25 11:22:50.782	9
8413	Pedro Gomes	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
651	Kevin	2	🥈 star	dune	2024-09-25 11:22:50.782	9
7212	Ben Broad | bbroad.eth 🎩🐹	2	🥈 star	dune	2024-09-25 11:22:50.782	9
368056	Fibo / Scryptoguy	2	🥈 star	dune	2024-09-25 11:22:50.782	9
362664	André Oliveira Cebola	2	🥈 star	dune	2024-09-25 11:22:50.782	9
409176	Hogan Prison no 619 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
391114	hayrisⓂ️🎩🎭🍖⚡️	2	🥈 star	dune	2024-09-25 11:22:50.782	9
1287	July	4	💎 vip	dune	2024-09-25 11:22:50.782	9
20270	erica	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
231371	Mat 🏴‍☠️.eth 🦩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
308284	Tushar12 🎩Ⓜ️  	2	🥈 star	dune	2024-09-25 11:22:50.782	9
378285	anco🐑	2	🥈 star	dune	2024-09-25 11:22:50.782	9
542351	Eren🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
415950	ranxdeer	2	🥈 star	dune	2024-09-25 11:22:50.782	9
10857	Nico Gallardo 🍄	2	🥈 star	dune	2024-09-25 11:22:50.782	9
342222	romandrits	2	🥈 star	dune	2024-09-25 11:22:50.782	9
8447	Erik	4	💎 vip	dune	2024-09-25 11:22:50.782	9
366713	nikolaii.base.eth 🚀	4	💎 vip	dune	2024-09-25 11:22:50.782	9
209586	tim/vortac	2	🥈 star	dune	2024-09-25 11:22:50.782	9
15838	Chinmay 🕹️🍿	2	🥈 star	dune	2024-09-25 11:22:50.782	9
668912	Ethereum Stories	2	🥈 star	dune	2024-09-25 11:22:50.782	9
2904	wake 🎩	4	💎 vip	dune	2024-09-25 11:22:50.782	9
409573	FCP	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
382802	Gina	2	🥈 star	dune	2024-09-25 11:22:50.782	9
453989	jaad, the degen 🎩🎰	2	🥈 star	dune	2024-09-25 11:22:50.782	9
308337	V5MT🎩🔵🫂↑Ⓜ️	2	🥈 star	dune	2024-09-25 11:22:50.782	9
9135	kugusha 🦋	4	💎 vip	dune	2024-09-25 11:22:50.782	9
230147	edit	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
7620	Cyber Shakti 🎩😇😈💃	2	🥈 star	dune	2024-09-25 11:22:50.782	9
237884	Mantine	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
309710	nomadicframe 🎩 🍔-'	2	🥈 star	dune	2024-09-25 11:22:50.782	9
12144	wbnns.base.eth 🔵	2	🥈 star	dune	2024-09-25 11:22:50.782	9
7657	greg	2	🥈 star	dune	2024-09-25 11:22:50.782	9
289295	Min 🎩 🇻🇳	2	🥈 star	dune	2024-09-25 11:22:50.782	9
238853	DavidBeiner	2	🥈 star	dune	2024-09-25 11:22:50.782	9
5254	Papajams	2	🥈 star	dune	2024-09-25 11:22:50.782	9
308426	senemsad	2	🥈 star	dune	2024-09-25 11:22:50.782	9
284616	andrew 🔵	2	🥈 star	dune	2024-09-25 11:22:50.782	9
1048	Mac Budkowski ᵏ	2	🥈 star	dune	2024-09-25 11:22:50.782	9
248216	sartocrates🃏	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
234616	Pichi 🟪🍖🐹🎩 🍡🌸	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
328041	Nicky Boost 🎩💎	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
5494	Jason	2	🥈 star	dune	2024-09-25 11:22:50.782	9
12152	Daniel - Bountycaster	2	🥈 star	dune	2024-09-25 11:22:50.782	9
198811	Anatoly Yakovenko	2	🥈 star	dune	2024-09-25 11:22:50.782	9
272116	🔵Bryce 🌭🍖🎭🧾	2	🥈 star	dune	2024-09-25 11:22:50.782	9
274272	Beatriz	2	🥈 star	dune	2024-09-25 11:22:50.782	9
398824	Irohcrypto 🍖🧾🎭✨	2	🥈 star	dune	2024-09-25 11:22:50.782	9
419722	Evan Mann	2	🥈 star	dune	2024-09-25 11:22:50.782	9
4019	Lata 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
7732	aneri.base.eth	2	🥈 star	dune	2024-09-25 11:22:50.782	9
276506	Sui	2	🥈 star	dune	2024-09-25 11:22:50.782	9
8451	Danica Swanson	2	🥈 star	dune	2024-09-25 11:22:50.782	9
426167	Kenji 🍖	2	🥈 star	dune	2024-09-25 11:22:50.782	9
4877	Trish🫧	2	🥈 star	dune	2024-09-25 11:22:50.782	9
409644	Alemac 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
528	0xen 🎩	4	💎 vip	dune	2024-09-25 11:22:50.782	9
427349	Dosir 🍖🐹	2	🥈 star	dune	2024-09-25 11:22:50.782	9
323501	Antonis Tsagaris 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
373	Jayme Hoffman	2	🥈 star	dune	2024-09-25 11:22:50.782	9
15126	intrepid ⛵️	2	🥈 star	dune	2024-09-25 11:22:50.782	9
3526	Surreal	2	🥈 star	dune	2024-09-25 11:22:50.782	9
440352	Ⓜ️ary.degen.eth 🎩🧾	2	🥈 star	dune	2024-09-25 11:22:50.782	9
1325	Cassie Heart	4	💎 vip	dune	2024-09-25 11:22:50.782	9
4434	chandresh 🪴	2	🥈 star	dune	2024-09-25 11:22:50.782	9
19105	Miss Angel 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
368278	Eduxdux	2	🥈 star	dune	2024-09-25 11:22:50.782	9
427386	Arun Hegden	2	🥈 star	dune	2024-09-25 11:22:50.782	9
4407	keccers	4	💎 vip	dune	2024-09-25 11:22:50.782	9
9391	iSpeakNerd 🧙‍♂️	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
11124	dusan.framedl.eth	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
4282	Matthew Fox 🌐	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
3854	Darryl Yeo 🛠️	2	🥈 star	dune	2024-09-25 11:22:50.782	9
18407	Sid	2	🥈 star	dune	2024-09-25 11:22:50.782	9
2282	Gökhan Turhan 🌞 gokhan.eth	2	🥈 star	dune	2024-09-25 11:22:50.782	9
5787	Chainleft	2	🥈 star	dune	2024-09-25 11:22:50.782	9
375140	Aislandart ⟠	2	🥈 star	dune	2024-09-25 11:22:50.782	9
403619	Maretus	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
268455	(ง'̀-'́)ง	2	🥈 star	dune	2024-09-25 11:22:50.782	9
368013	Ryan	2	🥈 star	dune	2024-09-25 11:22:50.782	9
309715	t0ma 🤌	2	🥈 star	dune	2024-09-25 11:22:50.782	9
502524	두부맘🐻‍❄️	2	🥈 star	dune	2024-09-25 11:22:50.782	9
297095	Pat Dimitri	2	🥈 star	dune	2024-09-25 11:22:50.782	9
409059	sx_zr04	2	🥈 star	dune	2024-09-25 11:22:50.782	9
376177	chillyazz🥷🏼🎴	2	🥈 star	dune	2024-09-25 11:22:50.782	9
18085	mleejr	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
387008	Anas.degen.eth Ⓜ️🎩🎭	2	🥈 star	dune	2024-09-25 11:22:50.782	9
244440	Shira Stember	2	🥈 star	dune	2024-09-25 11:22:50.782	9
212364	Mats	2	🥈 star	dune	2024-09-25 11:22:50.782	9
13833	Kaloh 	4	💎 vip	dune	2024-09-25 11:22:50.782	9
1315	manansh ❄️ 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
296315	Charlie	2	🥈 star	dune	2024-09-25 11:22:50.782	9
248111	Darkoh🍓🗣️	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
448502	Nima Leo 💎🔵	2	🥈 star	dune	2024-09-25 11:22:50.782	9
9138	Aghahowa.base.eth🔵🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
385387	Viz	2	🥈 star	dune	2024-09-25 11:22:50.782	9
3115	Ghostlinkz	2	🥈 star	dune	2024-09-25 11:22:50.782	9
239748	Vlady🎩Ⓜ️	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
270138	tknox.eth🟪🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
13893	Jared 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
218753	zora feed	2	🥈 star	dune	2024-09-25 11:22:50.782	9
274908	yjx278🧾🍖🎭	2	🥈 star	dune	2024-09-25 11:22:50.782	9
1580	Max Miner	2	🥈 star	dune	2024-09-25 11:22:50.782	9
698923	sukiyaki	2	🥈 star	dune	2024-09-25 11:22:50.782	9
10259	alex	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
834	Gabriel Ayuso	2	🥈 star	dune	2024-09-25 11:22:50.782	9
488178	Niko	2	🥈 star	dune	2024-09-25 11:22:50.782	9
415305	ReD 🎩🍖🧾	2	🥈 star	dune	2024-09-25 11:22:50.782	9
364883	littlecakes 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
218369	thej0n 🎩🍖🤝	2	🥈 star	dune	2024-09-25 11:22:50.782	9
428341	SODIQ OLAWALE	2	🥈 star	dune	2024-09-25 11:22:50.782	9
239933	s34n	2	🥈 star	dune	2024-09-25 11:22:50.782	9
207	timbeiko.eth	2	🥈 star	dune	2024-09-25 11:22:50.782	9
16098	Jorge Pablo Franetovic 🎩	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
420657	Zeph 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
308536	Zach Lipp	2	🥈 star	dune	2024-09-25 11:22:50.782	9
386213	🔵🎩Crpdaddy.⌐◨-◨	2	🥈 star	dune	2024-09-25 11:22:50.782	9
13994	Andrey Chagin🎩📸💎	2	🥈 star	dune	2024-09-25 11:22:50.782	9
576	Jonny Mack	4	💎 vip	dune	2024-09-25 11:22:50.782	9
4905	Max Jackson	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
230238	mvr 🐹	2	🥈 star	dune	2024-09-25 11:22:50.782	9
500235	dibo	2	🥈 star	dune	2024-09-25 11:22:50.782	9
193826	Pauline is based in Los Fomos	2	🥈 star	dune	2024-09-25 11:22:50.782	9
14260	Maning🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
324820	Sunny	2	🥈 star	dune	2024-09-25 11:22:50.782	9
416898	The Isolationist 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
311933	 Ⓜ️elissa Burr 🍓	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
381100	Snickerdoodle	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
265506	🎀 benna 🎀🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
14464	Brian Morris	2	🥈 star	dune	2024-09-25 11:22:50.782	9
16617	Herny🔵fomoeb✈️	2	🥈 star	dune	2024-09-25 11:22:50.782	9
562300	Mint Club Intern	2	🥈 star	dune	2024-09-25 11:22:50.782	9
1356	borodutch @ lunchbreak.com	2	🥈 star	dune	2024-09-25 11:22:50.782	9
247143	Kyle Patrick	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
389808	Disky.eth 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
15417	Ottis Ots	2	🥈 star	dune	2024-09-25 11:22:50.782	9
217261	Duxander |🔵	2	🥈 star	dune	2024-09-25 11:22:50.782	9
597941	✨🌸nato-san🌸✨	2	🥈 star	dune	2024-09-25 11:22:50.782	9
408681	Ryan 🏹	2	🥈 star	dune	2024-09-25 11:22:50.782	9
16066	Brad Barrish	2	🥈 star	dune	2024-09-25 11:22:50.782	9
323063	Jordi Gandul🎩✨🎭	2	🥈 star	dune	2024-09-25 11:22:50.782	9
14150	Jeff Excell 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
518129	Daniel 🎩 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
309242	deriniti 🎩🎭🍖✞	2	🥈 star	dune	2024-09-25 11:22:50.782	9
247018	SRΞΞ 🦉🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
377461	Krrbby.eth	2	🥈 star	dune	2024-09-25 11:22:50.782	9
422233	Emily 🎩🃏🍖	2	🥈 star	dune	2024-09-25 11:22:50.782	9
9528	Scott Kominers	2	🥈 star	dune	2024-09-25 11:22:50.782	9
296	Zach Davidson	2	🥈 star	dune	2024-09-25 11:22:50.782	9
15117	Jeff Jordan🔮🎩🧀	2	🥈 star	dune	2024-09-25 11:22:50.782	9
335383	entter	2	🥈 star	dune	2024-09-25 11:22:50.782	9
335242	Nicklas	2	🥈 star	dune	2024-09-25 11:22:50.782	9
9816	Camille Roux	2	🥈 star	dune	2024-09-25 11:22:50.782	9
18586	links 🏴	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
2755	Mike 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
211693	Mistershot🎩	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
3300	yashwant🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
490980	Magic Eden 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
315267	Avaaaaart🎩 🍖 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
436728	Stuart	2	🥈 star	dune	2024-09-25 11:22:50.782	9
617	Cameron Armstrong	4	💎 vip	dune	2024-09-25 11:22:50.782	9
1355	🗿 𝒃𝒊𝒂𝒔	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
354220	Gul Yildiz 🎩✨	2	🥈 star	dune	2024-09-25 11:22:50.782	9
2982	sparkz 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
417780	Vix	2	🥈 star	dune	2024-09-25 11:22:50.782	9
303	Kyle McCollom	2	🥈 star	dune	2024-09-25 11:22:50.782	9
18910	Maxbrain Capital  	2	🥈 star	dune	2024-09-25 11:22:50.782	9
10636	Jam 🐿️jamtogether	2	🥈 star	dune	2024-09-25 11:22:50.782	9
355110	Midnight Marauder 🐲💨	2	🥈 star	dune	2024-09-25 11:22:50.782	9
294370	Himmy 🎩🍖	2	🥈 star	dune	2024-09-25 11:22:50.782	9
880	accountless	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
304818	Sabato	2	🥈 star	dune	2024-09-25 11:22:50.782	9
11778	rohekbenitez🎩🎭Ⓜ️🍄	2	🥈 star	dune	2024-09-25 11:22:50.782	9
296241	Alexey 🎩🐲🐹	2	🥈 star	dune	2024-09-25 11:22:50.782	9
13267	cosmic-thinker.eth  🎩Ⓜ️	2	🥈 star	dune	2024-09-25 11:22:50.782	9
460229	Abs 🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
388401	Manytle	2	🥈 star	dune	2024-09-25 11:22:50.782	9
483462	Janicka	2	🥈 star	dune	2024-09-25 11:22:50.782	9
401818	Porky_Art🎩🎨📸	2	🥈 star	dune	2024-09-25 11:22:50.782	9
333868	Drachetech11 🎩🎭 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
385766	Fadil 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
18766	Samalz	2	🥈 star	dune	2024-09-25 11:22:50.782	9
330802	zolfaqqari	2	🥈 star	dune	2024-09-25 11:22:50.782	9
300986	Asha 🎩Ⓜ️	2	🥈 star	dune	2024-09-25 11:22:50.782	9
14345	kamtang.eth 🎩🍖🌭	2	🥈 star	dune	2024-09-25 11:22:50.782	9
21071	Layer3	2	🥈 star	dune	2024-09-25 11:22:50.782	9
9166	Noah Bragg 🐟	2	🥈 star	dune	2024-09-25 11:22:50.782	9
5034	tervo🗣️	2	🥈 star	dune	2024-09-25 11:22:50.782	9
13077	Naomi 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
194372	Roadu.𝓮𝓽𝓱 🎩🦊	2	🥈 star	dune	2024-09-25 11:22:50.782	9
236727	Sine	2	🥈 star	dune	2024-09-25 11:22:50.782	9
471309	Law❦︎	2	🥈 star	dune	2024-09-25 11:22:50.782	9
308588	Terry Bain	2	🥈 star	dune	2024-09-25 11:22:50.782	9
280798	Mohammed 🍖🔵 🎩🎭 🌳	2	🥈 star	dune	2024-09-25 11:22:50.782	9
431462	Richard 🎩Ⓜ️💎	2	🥈 star	dune	2024-09-25 11:22:50.782	9
11161	Alex Comeau 	2	🥈 star	dune	2024-09-25 11:22:50.782	9
362962	 Lukaa	2	🥈 star	dune	2024-09-25 11:22:50.782	9
332469	X ↑ FINDER	2	🥈 star	dune	2024-09-25 11:22:50.782	9
326040	Angelika Kollin 	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
248389	Dyl 🎩🎰🎶	2	🥈 star	dune	2024-09-25 11:22:50.782	9
14937	sgt_slaughtermelon🎩	2	🥈 star	dune	2024-09-25 11:22:50.782	9
294100	desultor 💀	2	🥈 star	dune	2024-09-25 11:22:50.782	9
348569	nabu	2	🥈 star	dune	2024-09-25 11:22:50.782	9
218142	Smash Thunder Stone 🎩🏹🧾	2	🥈 star	dune	2024-09-25 11:22:50.782	9
97	nic carter	2	🥈 star	dune	2024-09-25 11:22:50.782	9
347	Greg	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
16085	Samuel	3	🥇 influencer	dune	2024-09-25 11:22:50.782	9
6111	Funghibull	2	🥈 star	dune	2024-09-25 11:22:50.782	9
282520	$GEAUX ✝️🍖☕️	2	🥈 star	dune	2024-09-25 11:22:50.782	9
398978	Nat Eliason	2	🥈 star	dune	2024-09-25 11:22:50.782	9
\.


--
-- Name: TABLE pretrust_v2; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT ALL ON TABLE public.pretrust_v2 TO k3l_readonly;


--
-- PostgreSQL database dump complete
--

