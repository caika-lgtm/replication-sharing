---
theme: neversink
title: MIS Backend Sharing - DDIA Ch. 6 Replication
author: Cai Kaian
colorSchema: light
layout: cover
neversink_slug: "DDIA - Replication"
fonts:
  mono: 0xProto Nerd Font
  sans: Reforma 2018
  serif: Reforma 2018
  local: "0xProto Nerd Font, Reforma 2018"
defaults:
  color: rose-light
  transition: fade
  layout: top-title
---

# `6` Replication

MIS Backend Sharing: **Designing Data Intensive Applications**

<Email v="caika@sea.com" />

---

```yaml
layout: side-title
align: rm-lm
```

:: title ::

# Contents

<Cat :size="60" mood="shocked" color="#FDA7DC" v-drag="[147,210,60,60,-11]"/>

:: content ::

1. **Single-Leader Replication**
2. **Problems with Replication Lag**
3. Multi-Leader Replication
4. Leaderless Replication
5. Summary & Discussion

---

:: title ::

# Replication

:: content ::

<!-- It increases the ==availability== of data and allows for the use of the data in a different environment. -->
<!---->
<!-- <AdmonitionType type='note' > -->
<!-- This is note text -->
<!-- </AdmonitionType> -->

_Replication_ means keeping a copy of the _same data on multiple machines_ connected via a network.

Some reasons to do so include:

<v-clicks class='ns-c-fader'>

- Keep data geographically close to users, hence ==reducing access latency==
- Allows the system to continue working even if some of its parts have failed,
  hence ==increasing availability==
- Scale out number of machines that can serve read queries, hence ==increasing
  throughput==
- ==Offload complex queries and analytical processing== to a separate replica, preventing performance degradation on primary database

</v-clicks>

<v-click>

_Three_ families of algorithms for replication: ==Single-leader==, ==Multi-leader== and ==Leaderless==.

</v-click>

---

:: title ::

## Backups and Replication

:: content ::

_Backups_ are a form of replication, but they serve different purposes.

_Replicas_ ==quickly reflect writes== from one node on other nodes, but backups
store ==old snapshots== of data so that we can go back in time.

Often complementary to each other; backups are sometimes part of the process of
setting up replication.

---

```yaml
layout: side-title
align: rm-lm
```

:: title ::

# Single-Leader Replication

<Cat :size="60" mood="excited" color="#FDA7DC" v-drag="[186,188,60,60]"/>

:: content ::

- Synchronous Versus Asynchronous Replication
- Setting Up New Followers
- Handling Node Outages
- Implementation of Replication Logs

---

:: title ::

# Single Leader Replication

:: content ::

How do we ensure that ==every replica processes every write==?

<div class="ns-c-border">

**Single-Leader Replication**

<v-clicks class='ns-c-fader'>

1. One of the replicas is designated as the **leader**. All write requests are sent to the leader, which first writes the new data to its local storage.
2. The other replicas are **followers**. They receive a **replication log** from the leader after every write, and updates it local copy accordingly by applying all writes in the same order as they were processed by the leader.
3. Read requests can be served by either the leader or any follower. However, _writes are only accepted by the leader_; followers are read-only from client's point of view.

</v-clicks>

</div>

<v-click>

Very widely used; built-in feature of many relational databases (_PostgreSQL, MySQL, Oracle_), document databases (_MongoDB, DynamoDB_), message brokers (_Kafka_) and some network filesystems.

Many consensus algorithms (_Paxos, Raft_) are also based on the idea of a single leader. These algorithms are used in _CockroachDB, TiDB, etcd_, and _RabbitMQ_ quorum queues, to name a few.

</v-click>

---

:: title ::

## Synchronous Versus Asynchronous Replication

:: content ::

An important detail of a replicated system is whether it is _synchronous_ or _asynchronous_.

<v-click>

Here, the replication to follower 1 is _synchronous_: the leader ==waits for the follower to acknowledge== the write before it continues. The replication to follower 2 is _asynchronous_: the leader sends the message but ==doesn't wait== for a response.

</v-click>

<div class="flex flex-wrap">
<div class="w-7/10">

<v-click>

```mermaid {scale: 0.62}
sequenceDiagram
    actor U as User
    participant L as Leader
    participant F1 as Follower 1
    participant F2 as Follower 2

    U->>L: UPDATE ...
    activate L
    Note over L: waiting for followers' ok

    L->>F1: data change (replicate update)
    L->>F2: data change (replicate update)

    F1-->>L: ok
    L-->>U: ok
    deactivate L

    F2-->>L: ok (later)
```

</v-click>

</div>
<div class="w-3/10">
<v-click>

Normally, replication happens in _less than a second_.

However, source of delays include:

<div class="ns-c-tight">

- recovering from a ==failure==
- system is operating near ==maximum capacity==
- network is ==congested== between nodes

</div>
</v-click>
</div>
</div>

---

:: title ::

## Synchronous Versus Asynchronous Replication

:: content ::

<div class="flex flex-wrap">
<div class="w-4/10">
<div class="ns-c-center-item"><Thumb color="green-light" /></div><br />
<div class='ns-c-tight'>

- Follower _guaranteed_ to have up-to-date copy of data consistent with leader
- If leader fails, data is still available on follower

</div>
</div>
<div class="w-1/10"></div>
<div class="w-4/10">

<v-click>
<div class="ns-c-center-item"><Thumb color="red-light" dir="down" /></div><br />
<div class='ns-c-tight'>

- If synchronous follower doesn't respond (network fault, crash, etc.), write
  cannot be processed
- Leader has to block all writes until follower is available again

</div>
</v-click>
</div>
</div>

<v-click>

Impracticable for all followers to be synchronous. Instead, we can have ==one==
synchronous follower, and the others are asynchronous.

</v-click>
<v-click>

If the synchronous follower fails, one of the asynchronous followers is made synchronous. This configuration is sometimes called ==semi-synchronous==.

</v-click>
<v-click>

In some systems, a _majority_ of replicas is updated synchronously: a
==quorom==.

</v-click>

---

:: title ::

## Setting Up New Followers

:: content ::

When _increasing the number of replicas_ or _replacing failed nodes_, we need to set
up new followers.

<div class="ns-c-border">

**Setting Up New Followers**

<v-clicks class='ns-c-fader'>

1. Take a consistent snapshot of the leader's database. Most databases have this
   feature as it is also required for backups.
2. Copy the snapshot to the new follower.
3. The followers connects to the leader and requests for all the data changes that
   have happened since the snapshot was taken. This requires the snapshot to be
   associated with a position in the leader's replication log -- _PostgreSQL_
   calls this the _log sequence number_; _MySQL_ uses _binlog coordinates_ and
   _global transaction identifiers_ (GTIDs).
4. The follower is said to have _caught up_ once it has processed the backlog of
   changes since the snapshot. It can now process data changes from the leader
   as they happen.

</v-clicks>
</div>

---

:: title ::

## Handling Node Outages

:: content ::

<div class="flex flex-wrap">
<div class="w-4/10">

**Follower failure: Catch-up recovery**

<v-click>

Follower keeps track of all changes received from the leader on local disk.

On failure, can simply request for all changes since its last processed transaction.

</v-click>
<v-click>

However, if database has high write throughput, or if follower was offline for a long time, there might be a lot of writes to catch up on.

Leading to _high load on the recovering follower and leader_.

</v-click>
</div>
<div class="w-1/10"></div>
<div class="w-4/10">
<v-click>

**Leader failure: Failover**

Much trickier:

</v-click>
<div class="ns-c-tight">
<v-clicks class='ns-c-fader'>

- one of the followers needs to be ==promoted==
- clients need to be reconfigured to send writes to the new leader
- the other followers need to start consuming data from the new leader

</v-clicks>
<v-click>

==Failover== can happen manually (e.g. DBA) or automatically.

</v-click>
</div>
</div>
</div>

---

:: title ::

## Handling Node Outages

:: content ::

<div class="flex flex-wrap">
<div class="w-4/10">

An _automatic_ failover usually consists of:

<div class="ns-c-tight">
<v-clicks class='ns-c-fader'>

1. **Determining the leader has failed.** No foolproof way to know if leader has
   crashed or experienced a network failure; most systems use a _heartbeat_.
2. **Choosing a new leader.** Could be done through an _election_ process or
   appointed by a previously established _controller node_. Getting all nodes to
   agree on a leader is a _consensus problem_.
3. **Reconfiguring the system to use the new leader.** Need to handle the case
   of the old leader coming back.

</v-clicks>
</div>

</div>
<div class="w-1/10"></div>
<div class="w-4/10">
<v-click>

Many things can go wrong during the failover process:

</v-click>
<div class="ns-c-tight">
<v-clicks class='ns-c-fader'>

- Under asynchronous replication, the new leader might not have caught up with
  the old leader, leading to data loss.
- In certain fault scenarios, it could happen that two nodes both think they are
  the leader and accept writes, likely leading to data loss as well.
- What is the right timeout for the heartbeat? Too long: longer time to
  recovery; Too short: unnecessary failover during load spikes

</v-clicks>
</div>
</div>
</div>

---

```yaml
layout: quote
```

<Cat :size="120" mood="shocked" color="#FDA7DC" v-drag="[34,40,108,139]"/>

<StickyNote color="amber-light" textAlign="left" width="180px" v-drag="[128,-5,185,60,-9]">

.. and consensus
</StickyNote>

These issues -- node failures; unreliable networks; and trade-offs around
replica consistency, durability, availability, and latency -- are in fact
fundamental problems in distributed systems.

---

:: title ::

## Implementation of Replication Logs

:: content ::

**Statement-based replication**

Leader logs every write request that it executes and sends that statement log to its followers.

<v-click>

For a relational database: every `INSERT`, `UPDATE`, or `DELETE` statement.

Each follower parses and executes the SQL statement as if it has been received
from the client.

</v-click>
<v-click>

However, we run into issues if:

</v-click>
<div class="ns-c-tight">
<v-clicks class='ns-c-fader'>

- the statement calls a _non-deterministic function_ (e.g. `RAND()`, `NOW()`, `LIMIT` without `ORDER BY`)
- statements use an auto-incrementing column or depend on existing data in the
  database (e.g. `UPDATE ... WHERE <some condition>`); they must be executed in
  exactly the same order on each replica and can be limiting when there are
  multiple concurrent transactions
- statements with _side effects_ (e.g. triggers, stored procedures, user-defined functions), unless the side effects are absolutely deterministic

</v-clicks>
</div>

---

:: title ::

## Implementation of Replication Logs

:: content ::

**Write-ahead log (WAL) shipping**

In chapter 4 we saw that a WAL is needed to make B-tree storage engines robust.

<v-click>

Since the WAL contains all necessary information to restore the indexes and
heap, we can _use the WAL to build a replica_ on another node. This is used by
_PostgreSQL_ and _Oracle_, among others.

</v-click>
<v-click>

Main disadvantage: the log _describes data on a very low level_ -- which bytes
were changes in which disk blocks.

This ==couples replication to the storage engine and format==, which leads to issues
across database versions (e.g. cannot perform zero-downtime upgrades).

</v-click>
<v-click>

**Logical (row-based) log replication**

Decouple replication log from storage engine internals: use different log formats.
</v-click>
<v-click>

For relational databases, this is usually a sequence of records describing
writes to tables at row granularity.
</v-click>
<v-click>

Decoupling from storage engine internals allows easier _backward compatibility_.
Logical logs are also easier for external tools to consume (such as for
analytics, building indexes/caches, etc.), in a technique called ==change data
capture==.
</v-click>

---

```yaml
layout: side-title
align: rm-lm
```

:: title ::

# <mdi-code-json />

# Demo!

_MySQL + InnoDB_

:: content ::

```yaml
services:
  mysql-demo:
    image: mysql:8.0
    container_name: mysql-demo
    environment:
      MYSQL_ROOT_PASSWORD: root
    command: >
      --server-id=1
      --log-bin=mysql-bin
      --binlog-row-image=FULL
      --gtid-mode=ON
      --enforce-gtid-consistency=ON
      --innodb_flush_log_at_trx_commit=1
      --sync_binlog=1
      --innodb_redo_log_archive_dirs=demo:/var/lib/mysql-redo-archive
    volumes:
      - ./data1:/var/lib/mysql
      - ./redo-archive1:/var/lib/mysql-redo-archive
    ports: ["33061:3306"]
```

<v-click>

```bash
docker compose up -d
mycli mysql+aiomysql://root:root@127.0.0.1:33061
```

</v-click>

---

```yaml
layout: side-title
align: rm-lm
```

:: title ::

# <mdi-code-json />

# Demo!

_MySQL + InnoDB_

:: content ::

```sql
CREATE DATABASE demo;
USE demo;

CREATE TABLE t (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  n  INT NOT NULL,
  note VARCHAR(100),
  created_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  r DOUBLE,
  u CHAR(36)
) ENGINE=InnoDB;
```

---

```yaml
layout: side-title
align: rm-lm
```

:: title ::

# <mdi-code-json />

# Demo!

Statement-based replication

:: content ::

```sql {1|3,4|6,7|all}
SET SESSION binlog_format='STATEMENT';

INSERT INTO t(n, note, r, u)
VALUES (7, 'stmt', RAND(), UUID());

SHOW BINARY LOGS;
SHOW MASTER STATUS;
```

<v-after>

```bash
[11:26] 127.0.0.1 > SHOW BINARY LOGS;
+------------------+-----------+-----------+
| Log_name         | File_size | Encrypted |
+------------------+-----------+-----------+
| mysql-bin.000001 | 180       | No        |
| mysql-bin.000002 | 2994559   | No        |
| mysql-bin.000003 | 220       | No        |
| mysql-bin.000004 | 1164      | No        |
+------------------+-----------+-----------+

[11:26] 127.0.0.1 > SHOW MASTER STATUS;
+------------------+----------+--------------+------------------+-------------------+
| File             | Position | Binlog_Do_DB | Binlog_Ignore_DB | Executed_Gtid_Set |
+------------------+----------+--------------+------------------+-------------------+
| mysql-bin.000004 | 1164     |              |                  | b55d687c-fb2f-... |
+------------------+----------+--------------+------------------+-------------------+
```

</v-after>

---

```yaml
layout: side-title
align: rm-lm
```

:: title ::

# <mdi-code-json />

# Demo!

Statement-based replication

:: content ::

```bash
mysqlbinlog --read-from-remote-server \
  --host=127.0.0.1 \
  --port=33061 \
  -uroot -p \
  -vv mysql-bin.000004 \
| tail -n 80
```

---

```yaml
layout: side-title
align: rm-lm
```

:: title ::

# <mdi-code-json />

# Demo!

Statement-based replication

:: content ::

```ini{*|1-3|4-7|8,13-15,25|9-11|16,17|18,19|20-23|26,27|*}
#260127 11:26:28 server id 1  end_log_pos 832 CRC32 0xd0a47567 	GTID	last_committed=2	sequence_number=3	rbr_only=no	original_committed_timestamp=1769484388203704	immediate_commit_timestamp=1769484388203704	transaction_length=411
# original_commit_timestamp=1769484388203704 (2026-01-27 11:26:28.203704 +08)
# immediate_commit_timestamp=1769484388203704 (2026-01-27 11:26:28.203704 +08)
/*!80001 SET @@session.original_commit_timestamp=1769484388203704*//*!*/;
/*!80014 SET @@session.original_server_version=80045*//*!*/;
/*!80014 SET @@session.immediate_server_version=80045*//*!*/;
SET @@SESSION.GTID_NEXT= 'b55d687c-fb2f-11f0-8a73-7a5258f3989d:8'/*!*/;
# at 832
#260127 11:26:28 server id 1  end_log_pos 918 CRC32 0x7a7ece1a 	Query	thread_id=8	exec_time=0	error_code=0
SET TIMESTAMP=1769484388.191496/*!*/;
BEGIN
/*!*/;
# at 918
# at 950
# at 989
#260127 11:26:28 server id 1  end_log_pos 950 CRC32 0x623e02ab 	Intvar
SET INSERT_ID=1/*!*/;
#260127 11:26:28 server id 1  end_log_pos 989 CRC32 0xd97784a7 	Rand
SET @@RAND_SEED1=229396595, @@RAND_SEED2=1034435055/*!*/;
#260127 11:26:28 server id 1  end_log_pos 1133 CRC32 0xb44f6417 	Query	thread_id=8	exec_time=0	error_code=0
SET TIMESTAMP=1769484388.191496/*!*/;
INSERT INTO t(n, note, r, u)
VALUES (7, 'stmt', RAND(), UUID())
/*!*/;
# at 1133
#260127 11:26:28 server id 1  end_log_pos 1164 CRC32 0x648b783a 	Xid = 35
COMMIT/*!*/;
```

<StickyNote color="indigo-light" textAlign="left" width="300px" v-drag="[306,103,496,246]" v-click="['1']"  title="GTID Event Header">
<div class="ns-c-tight">

- marks start of transaction
- assigns a global transaction identifier (GTID)
- `last_committed`/`sequence_number` -- used for parallel replication
  (dependency tracking)
- `rbr_only=no` -- transaction is not "row-based only"
- `original_committed_timestamp`/`immediate_commit_timestamp` -- "original" for
  upstream commit time, "immediate" is when this server committed
- `transaction_length` -- length of transaction in bytes
</div>
</StickyNote>
<StickyNote color="indigo-light" textAlign="left" width="300px" v-drag="[330,180,400,135]" v-click="['2']" title="Versioned Session Settings">
<div class="ns-c-tight">

- `/*!800xx ... */` are version-conditional statements -- only executed on
  servers with version `xx` or higher
- `SET @@SESSION.GTID_NEXT= '...:8'` -- next transaction will use this GTID
</div>
</StickyNote>
<StickyNote color="indigo-light" textAlign="left" width="300px" v-drag="[380,250,280,135]" v-click="['3']"  title="Byte Offsets">
<div class="ns-c-tight">

- _Byte offsets_ where each event starts
- `end_log_pos 950` -- byte offset immediately after this event ends
</div>
</StickyNote>
<StickyNote color="indigo-light" textAlign="left" width="300px" v-drag="[350,250,300,130]" v-click="['4']"  title="Query Event: BEGIN">
<div class="ns-c-tight">

- marks start of transaction
- `SET TIMESTAMP` to pin the session time for time-sensitive behaviour (e.g.
`NOW()`)
</div>
</StickyNote>
<StickyNote color="indigo-light" textAlign="left" width="300px" v-drag="[300,150,350,150]" v-click="['5']"  title="Intvar Event">
<div class="ns-c-tight">

- extra metadata MySQL logs to make statement re-execution _deterministic_
- without this, auto-increment allocation can diverge
- log extra _session state_ to replay statements safely
</div>
</StickyNote>
<StickyNote color="indigo-light" textAlign="left" width="300px" v-drag="[300,240,280,100]" v-click="['6']"  title="Rand Event">
<div class="ns-c-tight">

- capture RNG seeds so `RAND()` replays to same value
</div>
</StickyNote>
<StickyNote color="indigo-light" textAlign="left" width="300px" v-drag="[300,235,280,140]" v-click="['7']"  title="Query Event">
<div class="ns-c-tight">

- the actual DML statement text; core of statement-based replication
- `RAND()` can be controlled via seeds, but `UUID()` is non-deterministic
</div>
</StickyNote>
<StickyNote color="indigo-light" textAlign="left" width="300px" v-drag="[300,320,270,140]" v-click="['8']"  title="Xid Event">
<div class="ns-c-tight">

- `Xid` is the transaction commit event
- `35` is internal transaction identifier
- marks replication boundary
</div>
</StickyNote>

---

```yaml
layout: side-title
align: rm-lm
```

:: title ::

# <mdi-code-json />

# Demo!

Logical log replication

:: content ::

```sql {1|3,4|all}
SET SESSION binlog_format='ROW';

INSERT INTO t(n, note, r, u)
VALUES (8, 'row', RAND(), UUID());
```

<v-after>

```bash {6}
mysqlbinlog --read-from-remote-server \
  --host=127.0.0.1 \
  --port=33061 \
  -uroot -p \
  -vv \
  --base64-output=DECODE-ROWS \
  mysql-bin.000004 \
| tail -n 80
```

</v-after>

---

```yaml
layout: side-title
align: rm-lm
```

:: title ::

# <mdi-code-json />

# Demo!

Logical log replication

:: content ::

```ini {*|1-3|5-7|9-18|*}
#260127 13:10:45 server id 1  end_log_pos 1243 CRC32 0xda69ed31 	GTID	last_committed=3
# sequence_number=4	rbr_only=yes	original_committed_timestamp=1769490645283253	immediate_commit_timestamp=1769490645283253	transaction_length=357
/*!50718 SET TRANSACTION ISOLATION LEVEL READ COMMITTED*//*!*/;

#260127 13:10:45 server id 1  end_log_pos 1385 CRC32 0xdce34814 	Table_map:
# `demo`.`t` mapped to number 93
# has_generated_invisible_primary_key=0

#260127 13:10:45 server id 1  end_log_pos 1490 CRC32 0x5889d2a9 	Write_rows:
# table id 93 flags: STMT_END_F
### INSERT INTO `demo`.`t`
### SET
###   @1=2 /* LONGINT meta=0 nullable=0 is_null=0 */
###   @2=8 /* INT meta=0 nullable=0 is_null=0 */
###   @3='row' /* VARSTRING(400) meta=400 nullable=1 is_null=0 */
###   @4=1769490645.272466 /* TIMESTAMP(6) meta=6 nullable=0 is_null=0 */
###   @5=0.38067036064404097262 /* DOUBLE meta=8 nullable=1 is_null=0 */
###   @6='88f4642e-fb3e-11f0-89d9-265234713e18' /* STRING(144) meta=65168 nullable=1 is_null=0 */
```

<StickyNote color="indigo-light" textAlign="left" width="300px" v-drag="[239,176,344,146]" v-click="['1']"  title="GTID Event">
<div class="ns-c-tight">

- `rbr_only=yes` -- transaction is "row-based only" (no statement events)
- isolation level is `READ COMMITTED` -- matters for consistent replay / tooling
</div>
</StickyNote>
<StickyNote color="indigo-light" textAlign="left" width="300px" v-drag="[239,250,344,146]" v-click="['2']"  title="Table_map Event">
<div class="ns-c-tight">

- map table ID to table metadata ("table id 93 refers to `demo.t`")
- enough metadata so that replica knows how to interpret column images
</div>
</StickyNote>
<StickyNote color="indigo-light" textAlign="left" width="300px" v-drag="[239,90,450,146]" v-click="['3']"  title="Write_rows Event">
<div class="ns-c-tight">

- the actual logical row image; includes the actual column values
- `@1` corresponds to the 1st column in the table definition, `id`
- generated UUID string is already fixed in `@6`
- timestamp is fixed in `@4`
</div>
</StickyNote>

---

:: title ::

### Which MySQL `binlog` format to use?

:: content ::

_MySQL_ comes with three binary log formats -- `STATEMENT`, `ROW`, and `MIXED`.
Let's evaluate each one.

<v-click>

**STATEMENT**

</v-click>
<div class="flex flex-wrap">
<div class="w-4/10">
<div class='ns-c-tight'>
<v-clicks class='ns-c-fader'>

- _Smaller binlogs_ for operations that touch many rows (e.g. `UPDATE big_tab
SET flag = 1 WHERE ...`) -- less network/storage
- _Human-auditable_ -- helpful for debugging or compliance
- Can be faster when used with deterministic functions producing large generated
  values

</v-clicks>
</div>
</div>
<div class="w-1/10"></div>
<div class="w-4/10">

<v-click>

_but..._

</v-click>
<div class='ns-c-tight'>
<v-clicks class='ns-c-fader'>

- _Correctness risk_ for unsafe/non-deterministic statements
- _Sensitive_ to differences in source/replica environments: time zones,
  collation quirks, etc.

</v-clicks>
</div>
<v-click>

_SBR_ ==only for specific workflows==:

</v-click>
<div class="ns-c-tight">
<v-clicks class='ns-c-fader'>

- dominated by _large set-based changes_ -- RBR will explode binlog volume
- deterministic statements, control over environment
- need for _readable/auditable_ binlogs

</v-clicks>
</div>
</div>
</div>

---

:: title ::

### Which MySQL `binlog` format to use?

:: content ::

**ROW**

<div class="flex flex-wrap">
<div class="w-4/10">
<div class='ns-c-tight'>
<v-clicks class='ns-c-fader'>

- _Most correct/least surprising_ -- avoids "unsafe statements" issue
- Handles non-determinism by logging the materialized values
- Not as dependent on "SQL-level compatibility"

</v-clicks>
</div>
</div>
<div class="w-1/10"></div>
<div class="w-4/10">

<v-click>

_but..._

</v-click>
<div class='ns-c-tight'>
<v-clicks class='ns-c-fader'>

- _Bigger binlogs_ (often significantly) -- impacts storage, network and
  throughput
- _Harder to audit_ -- can't see the original SQL

</v-clicks>
</div>
<v-click>

==Default choice==, especially with any non-determinism, triggers, stored routines,
etc.

</v-click>
</div>
</div>

---

:: title ::

### Which MySQL `binlog` format to use?

:: content ::

**MIXED**

Logs statements by default, but automatically switches to _ROW_ for statements
MySQL considers unsafe.

<div class="flex flex-wrap">
<div class="w-4/10">
<div class='ns-c-tight'>
<v-clicks class='ns-c-fader'>

- _Pragmatic compromise_ -- keeps binlog smaller for safe statements, avoids
  correctness issues for unsafe statements
- Good for "mostly readable SQL"

</v-clicks>
</div>
</div>
<div class="w-1/10"></div>
<div class="w-4/10">

<v-click>

_but..._

</v-click>
<div class='ns-c-tight'>
<v-clicks class='ns-c-fader'>

- Mix of query events and row events -- depends on safeness rules and context
- Inherits some SBR sensitivity

</v-clicks>
</div>
<v-click>

Useful to deal with pressure on binlog volume/network while still being able to
handle unsafe statements.

</v-click>
</div>
</div>

---

```yaml
layout: side-title
align: rm-lm
```

:: title ::

# Problems with Replication Lag

<Cat :size="60" mood="ko" color="#FDA7DC" v-drag="[269,187,60,60,17]"/>

:: content ::

- Reading Your Own Writes
- Monotonic Reads
- Consistent Prefix Reads
- Solutions for Replication Lag

<img src="/images/cat-what.gif" v-drag="[768,56,148,129]"/>

---

:: title ::

# Problems with Replication Lag

:: content ::

Leader-based replication enables a _read-scaling_ architecture: we can increase
capacity for read-only requests by simply adding more replicas.

<v-click>

However, if an application reads from an _asynchronous_ replica, it may see
==stale information== if the follower has fallen behind, leading to apparent
==inconsistencies==.
</v-click>

<Admonition title="Info" color="indigo-light" width="300px" v-drag="[53,215,489,88]" v-click>

This inconsistency is only a temporary state; the followers will eventually
catch up and become consistent, hence the term _eventual consistency_.

</Admonition>
<AdmonitionType type="warning" width="300px" v-drag="[53,320,489,88]" v-click>

The term "eventually" is intentionally vague; in general there is no limit to
how far a replica can fall behind -- minutes to even hours.

</AdmonitionType>

<img src="/images/eventually.jpg" v-drag="[634,202,220,289]" v-click="'3'"  />

---

:: title ::

## Reading Your Own Writes

:: content ::

Consider a scenario where a user submits some data and then view what they submitted. The write can only be processed by the leader, but the read can be served by any replica.

<v-click>

```mermaid {scale: 0.75}
sequenceDiagram
    actor U as User
    participant L as Leader
    participant F as Follower

    U->>L: write comment
    activate L
    L-->>U: ok
    deactivate L

    U->>F: read comments
    Note over U,F: replication lag
    F-->>U: empty

    L->>F: replicate write (async)
```

</v-click>
<v-click>

<Admonition title="Read Your Writes" color="indigo-light" width="300px" v-drag="[545,171,423,88]">

If a process performs a write $w$, and that same process performs a subsequent read $r$, then $r$ must observe $w$'s effects.
</Admonition>
<img src="/images/jepsen_consistency.png" v-drag="[546,270,391,246]" />

</v-click>

---

:: title ::

## Reading Your Own Writes

:: content ::

<div class="flex flex-wrap">
<div class="w-4/10">
<div class='ns-c-tight'>

Some techniques to implement _read-your-writes_ consistency:
<v-clicks class='ns-c-fader'>

- Read resources that users can _modify_ from the leader or a synchronous follower
- Track _last update time_ and for one minute afterwards, only read from the leader; or from followers with less than one minute replication lag
- Timestamp can be _logical timestamp_ (such as log sequence number) or wall
  clock time (in which case we need to consider clock synchronization)

</v-clicks>
</div>
</div>
<div class="w-1/10"></div>
<div class="w-4/10">

<v-click>

What about same user, multiple devices?

</v-click>
<div class='ns-c-tight'>
<v-clicks class='ns-c-fader'>

- Need to centralize 'last update' metadata
- For replicas distributed across different _regions_, need to consider that
  connections from different devices can be routed to different regions (home
  broadband connection vs. cellular data network)

</v-clicks>
</div>
<v-click>
</v-click>
</div>
</div>

---

:: title ::

### Regions and Availability Zones

:: content ::

<div class="flex flex-wrap">
<div class="w-4/10">

<v-click>

_DDIA_ uses ==region== to refer to _one or more datacenters_ in a single geographic
location.
</v-click>
<v-click>

Cloud providers locate multiple datacenters in the same geographic region.

Each _datacenter_ is referred to as an ==availability zone== or just ==zone==.
</v-click>
<v-click>

Zones in the same region are connected by **very high speed networks**, with latency
low enough that that most distributed systems can run with nodes spread across
multiple zones in the same region.
</v-click>

</div>
<div class="w-1/10"></div>
<div class="w-4/10">
<v-click>

**Region Key**: _{area}-{country}-{region idx}_

**AZ**: _Logical_ datacenter that consist of one or more datacenters.

**Segment**: Network segments to achieve _network isolation_.

</v-click>
<v-click>

For example, _Infra Center_ is deployed in the AZ `ap-sg-1-general-b`, which is
served by IDCs _AirTrunk B, AirTrunk D, AirTrunk C_, and is in the _General_ segment.

Let's take a look at [AZ Meta CMDB](https://space.shopee.io/azmeta/platform/meta_management/az).
</v-click>

</div>
</div>

---

:: title ::

## Monotonic Reads

:: content ::

If a user makes several reads from ==different replicas== (e.g. refreshing a
page and having requests routed to random servers) -- first to a follower
with little lag, then to a follower with greater lag -- is is possible to see
things _move backwards_ in time.

<v-click>

```mermaid {scale: 0.65}
sequenceDiagram
    actor U as User
    participant L as Leader
    participant F1 as Follower 1
    participant F2 as Follower 2

    U->>F1: read item
    F1-->>U: v2 (newer)

    Note over U: next read hits <br> a different replica

    U->>F2: read item
    Note over U,F2: F2 is behind
    F2-->>U: v1 (older)

    Note over U: monotonic reads <br> violated
```

</v-click>
<v-click>

<Admonition title="Monotonic Reads" color="indigo-light" width="300px" v-drag="[593,158,350,112]">

If a process performs read $r_1$, then $r_2$, then $r_2$ cannot observe a state
prior to the writes which were reflected in $r_1$.
</Admonition>
<img src="/images/jepsen_consistency.png" v-drag="[577,278,392,241]" />

</v-click>

---

```yaml
margin: tight
```

:: title ::

## Consistent Prefix Reads

:: content ::

```mermaid {scale: 0.57}
sequenceDiagram
    autonumber
    actor A as Yi Xiang
    actor B as Kaian
    participant L as Leader
    participant P as Posts replica
    participant R as Replies replica
    actor C as Yao Xuan

    A->>L: post "Lunch?"
    L-->>A: ok
    L->>P: replicate post (slow)

    B->>L: reply "No, I brought my own food"
    L-->>B: ok
    L->>R: replicate reply (fast)

    C->>R: read thread (replies)
    C-->>R: (has reply)
    Note over C,R: sees reply first
    R-->>C: "No, I brought my own food"

    C->>P: read thread (posts)
    Note over C,P: question arrives later
    P-->>C: (later) "Lunch?"
```

---

:: title ::

## Consistent Prefix Reads

:: content ::

The ==casual== dependency `lunch? -> no` has been violated. This is a particular
problem in sharded/partitioned databases, where there is no global ordering of
writes.

<v-click>

<Admonition title="Causal Consistency" color="indigo-light" width="450px">

Causally-related operations should appear in the same order on all processes --
though processes may disagree about the order of casually independent operations.

Causal consistency is _sticky available_. A total order will give us _sequential consistency_, at the cost of availability. More [here](https://jepsen.io/consistency/models).
</Admonition>

<img src="/images/jepsen_consistency.png" v-drag="[514,120,457,316]" />

</v-click>
<v-click>

How do we keep track of causal dependencies?
</v-click>

---

:: title ::

## Solutions for Replication Lag

:: content ::

For an eventually consistent system, we need to consider how the application
behaves if the replication lag increases to several minutes or even hours.

If it is not acceptable, we need to design the system to provide ==stronger guarantees==.

<v-click>

We have mentioned some solutions using ==application code== to provide a stronger guarantee than the underlying database, but this is complex and easy to get wrong.

</v-click>
<v-click>

Easiest: choose a database that provides strong consistency guarantees (such as _linearizability_), while offering the fault tolerance, high availability, and scalability advantages of a distributed database (_NewSQL_).

Examples include _CockroachDB_, _TiDB_, and _Google Cloud Spanner_.

</v-click>
<v-click>

Trade-offs? Higher overheads, worse performance, reduced availability during
network partitions.

</v-click>

<img src="/images/spanner.png" v-click="'2'" v-drag="[611,404,96,96]" />

<img src="/images/tidb.png" v-click="'2'" v-drag="[406,423,165,65]" />

<img src="/images/cockroachdb.jpg" v-click="'2'" v-drag="[108,389,248,130]" />

---

```yaml
layout: side-title
align: rm-lm
```

:: title ::

# Multi-Leader Replication

<Cat :size="60" mood="happy" color="#FDA7DC" v-drag="[100,189,60,60]"/>

:: content ::

- Geographically Distributed Operation
- Dealing with Conflicting Writes
- CDRTs and Operational Transformations

<img src="/images/spiderman.webp" v-drag="[109,331,197,157]"/>

---

:: title ::

## Geographically Distributed Operation

:: content ::

One natural way to arrive at a multi-leader configuration is to have a ==leader in
each _region_== we have replicas in (known as _geographically distributed_,
_geo-distributed_, or _geo-replicated_).

<img src="/images/geo_dist.png" v-drag="[24,166,528,256]" v-click />

<div class="flex flex-wrap">
<div class="w-6/10"></div>
<div class="w-4/10">
<div class='ns-c-tight'>
<v-clicks class='ns-c-fader'>

- ==Inter-region== network delay is now hidden from users
- Better tolerance of _regional outages_; each region can operate independently
- Less sensitive to unreliable network traffic _between regions_
- **Biggest downside**: cannot provide ==strong consistency== guarantees seen in
  single-leader systems
- Need to consider the _replication topology_ (e.g. _circular, star, all-to-all_) and the problems that come with each

</v-clicks>
</div>
</div>
</div>

---

:: title ::

## Dealing with Conflicting Writes

:: content ::

How do we resolve conflicts arising from ==concurrent writes==?

<Admonition title="Concurrent Writes" color="indigo-light" width="600px" v-click>

What does it mean for two writes to be _concurrent_? Intuitively, we can think
of concurrent writes as two writes that not "aware" of the other at the time the
write was originally made. It does not necessarily mean that the writes happen
at the same wall clock time.

We will formalize this when discussing the _happens-before_ relation.
</Admonition>

<v-click>

**Conflict Avoidance**

Avoid conflicts in the first place.

Consider an app where the user can only edit their own data. Then we just need
to route all requests from a particular use to the same "home" region.

Another example: for two leaders to assign unique IDs based on an auto-incrementing counter, we can have one leader only generate odd numbers while the other only generates even.

</v-click>

---

:: title ::

## Dealing with Conflicting Writes

:: content ::

**Last write wins**

Attach a timestamp to each write and use it to decide which write to keep.

For applications where lost updates are acceptable.

<AdmonitionType type="warning" title="Timestamps" color="orange-light" width="600px" v-click>

To avoid running into clock synchronization issues, we usually use a _logical
clock_ instead of wall clock time (e.g. Unix timestamps).
</AdmonitionType>

<v-click>

**Manual Conflict Resolution**

We have all resolved merge conflicts in Git before. 🥺

Instead of manually intervening for all conflicts in real time, we can store
both values being written (termed _sibilings_) and return both values when
queried.

The conflict can then be resolved in application code or by prompting the user.

</v-click>

---

:: title ::

## Dealing with Conflicting Writes

:: content ::

**Automatic Conflict Resolution**

Have an algorithm automatically merge concurrent writes into a consistent state,
ensuring all replicas _converge_.

There are many algorithms designed for different data types: _text, integers, key-value mapping_, or a _collection of items_ like a to-do list or shopping cart.

There are limits to what is possible with automatic conflict resolution, but it
is sufficient for most applications.

---

:: title ::

## CDRTs and Operational Transformations

:: content ::

**Conflict-free Replicated Data Types** (CDRTs) and **Operational Transformations**
(OTs) are two families of algorithms commonly used for automatic conflict
resolution.

Each has their own performance and functionality trade-offs. _OT_ is most
commonly used for real-time collaborative editing of text (e.g. Google Docs),
while _CDRTs_ can be found in distributed databases such as Redis Enterprise,
Riak, and Azure Cosmos DB.

<img src="/images/cdrt_ot.png" v-drag="[124,229,768,280]" v-click/>

---

:: title ::

### What is a conflict?

:: content ::

Some kinds of conflicts are obvious, while others can be more subtle.

<v-click>

Consider **GBooking**,

</v-click>
<div class='ns-c-tight'>
<v-clicks class='ns-c-fader'>

- track which of our meeting rooms are booked by which groups of people at which time
- need to ensure no overlapping bookings
- conflict may arise if two different bookings are created for the same room at the same time
- especially if two bookings are made on two different leaders (e.g. _Sea_ and
  _Shopee_)

</v-clicks>
</div>

---

```yaml
layout: side-title
align: rm-lm
```

:: title ::

# Leaderless Replication

<Cat :size="60" mood="lovestruck" color="#FDA7DC" v-drag="[247,309,60,60,180]"/>

:: content ::

- Writing to the Database When a Node Is Down
- Limitations of Quorum Consistency
- Single-Leader vs. Leaderless Replication Performance
- Detecting Concurrent Writes

---

:: title ::

# Leaderless Replication

:: content ::

So far, we have a leader that determines the order in which writes should be
processed, and followers apply the leader's writes in the same order.

<v-click>

Some storage systems take a different approach: allow ==any replica== to directly
accept writes.
</v-click>
<v-click>

In some leaderless implementations, the client sends its writes to several
replicas, while in others, a ==coordinator node== does this on behalf of the client.
</v-click>
<v-click>

_Riak_, _Cassandra_, and _ScyllaDB_ are open source databases with leaderless
replication models.

<img src="/images/riak.png" v-drag="[176,363,152,49]" />

<img src="/images/cassandra.png" v-drag="[406,335,155,104]" />

<img src="/images/scylladb.png" v-drag="[626,334,115,115]" />

</v-click>

---

:: title ::

## Writing to the Database When a Node Is Down

:: content ::

In single-leader configurations, if the leader fails we can perform a _failover_. In a leaderless configuration, the failed replica simply ==misses the write==.

<v-click>

To handle ==stale responses== from the node after it comes back online, _read
requests are send to several replicas in parallel_, and we simply take the value
with the greatest timestamp.
</v-click>
<v-click>

**Catching up on missed writes**
</v-click>

<div class="ns-c-tight">
<v-clicks class='ns-c-fader'>

- ==Read repair==: the client can write the latest value to replicas that
  returned stale responses
- ==Hinted handoff==: another replica store writes on the behalf of the failed
  node in the form of _hints_, which are sent when the node recovers; handles
  values that are never read and missed out by _read repair_
- ==Anti-entropy==: a background process that periodically looks for differences
  in data between replicas and copies missing data from one replica to another

</v-clicks>
</div>

---

:: title ::

## Writing to the Database When a Node Is Down

:: content ::

**Quorums for reading and writing**

Consider a simple example where we have three replicas and we only accept writes
if it was processed by at least two of the replicas. This means that at most one
replica can be stale.

If we read from at least two replicas, we can guarantee
that at least one of the two values is up to date.

<v-click>

More generally, assume we have $n$ replicas and require every write to be confirmed
by at least $w$ nodes, with at least $r$ nodes for each query. Then as long as
$w + r > n$ we can guarantee an up-to-date value when reading.
</v-click>
<v-click>

Reads and writes that obey these $r$ and $w$ values are called ==quorum reads
and writes==.
</v-click>
<v-click>

These parameters $n, w, r$ are typically configurable:
</v-click>

<div class="ns-c-tight">
<v-clicks class='ns-c-fader'>

- make $n$ odd (typically 3 or 5) and set $w = r = \lceil\frac{n + 1}{2}\rceil$
- for read-heavy workloads, $w = n$ and $r = 1$

</v-clicks>
</div>

---

:: title ::

## Limitations of Quorum Consistency

:: content ::

Even with $w + r > n$, there are still edge cases to consider:

<div class="ns-c-tight">
<v-clicks class='ns-c-fader'>

- if a node carrying a new value fails and is restored from a replica carrying
  stale data, the number of replicas holding the new value can fall below $w$,
  breaking quorum condition
- when a _rebalancing_ is in progress, nodes may have inconsistent views of
  which nodes should be holding the $n$ replicas for a particular key
- if wall clock time is used as a timestamp to determine which write is newer
  (as in _Cassandra_ and _ScyllaDB_), some writes might get silently dropped if
  another node with faster clock writes to the same key
- concurrent writes $w_1, w_2$ still pose an issue: one replica can process $w_1 \rightarrow w_2$ while another replica processes $w_2 \rightarrow w_1$
</v-clicks>
</div>

---

:: title ::

## Single-Leader vs. Leaderless Replication Performance

:: content ::

In single-leader replication, if we require up-to-date reads we need to query
the leader, which **limits read throughput**, is prone to **failovers** and is
sensitive to **performance degradation**.

<v-click>

A leaderless architecture is more resilient against such issues as requests go
to multiple replicas and we use the fastest responses. This is called **request hedging** and significantly _reduces tail latency_.
</v-click>
<v-click>

Leaderless systems is not free from performance issues as well:
</v-click>

<div class="ns-c-tight">
<v-clicks class='ns-c-fader'>

- need to detect when another replica is down so as to store hints; handoff
  process also puts additional loads on the replicas
- more replicas $\implies$ bigger quorums $\implies$ more likely to hit a slow
  replica
- network partitions can make it impossible to reach quorums

</v-clicks>
</div>

---

:: title ::

## Detecting Concurrent Writes

:: content ::

As with multi-leader replication, leaderless databases allow concurrent writes
to the same key, resulting conflicts that need to be resolved. Such conflicts may occur as the writes happen, or are detected later during read repair, hinted handoff, or anti-entropy.

<v-click>

Events may arrive in a ==different order at different nodes==, due to _variable
network delays and partial failures_.
</v-click>
<v-click>

To achieve eventual consistency, the replicas should converge toward the same
value using the previously discussed conflict resolution algorithms.

</v-click>
<v-click>

**How do we decide whether two operations are concurrent?**

</v-click>
<div class='ns-c-tight'>
<v-clicks class='ns-c-fader'>

- $A$ `INSERT`s some value and $B$ `UPDATE`s that value: ==not concurrent==, $B$'s
  operation builds upon $A$'s; we say that $B$ is causally dependent on $A$
- $A$ does `SET x = 1` and $B$ does `SET x = 2`: ==concurrent==; each client does
  not know that the other is performing a write on the same key

</v-clicks>
</div>

---

:: title ::

### The "happens-before" relation

:: content ::

Informally, an operation $A$ ==happens-before== an operation $B$ if $B$ knows
about $A$, or depends on $A$, or builds upon $A$ in some way.

<v-click>

Two operations are said to be ==concurrent== if neither _happens-before_ the
other.
</v-click>
<v-click>

Thus for any two operations $A$ and $B$, we have
</v-click>

<div class="ns-c-tight">
<v-clicks class='ns-c-fader'>

- $A$ happens-before $B$, or
- $B$ happens-before $A$, or
- $A$ and $B$ are concurrent

</v-clicks>
</div>

<v-click>

$\xrightarrow{happened-before}$ is a _strict partial order_ on events in a concurrent system.

If $A \xrightarrow{} B$, then $B$ should overwrite $A$, but if $A$ and $B$
are concurrent, then we have a conflict that needs to be resolved.
</v-click>

---

```yaml
layout: section
```

# Summary

Key takeaways?

<Ghost :size="60" mood="excited" color="#FDA7DC" v-drag="[79,180,60,60]"/>

---

:: title ::

## Summary

:: content ::

_Replication_ serves many purposes: **high availability, disconnect operation,
reduce latency, scalability**, etc.

<v-click>

Three main approaches -- **Single-leader**, **Multi-leader**, and **Leaderless** --
each with their own trade-offs.
</v-click><v-click>

_Single-leader_ is the most common approach as it is easier to understand and **offers strong consistency guarantees**, while the other two can be **more robust** in presence of faulty nodes, network partitions, and latency spikes (but at the cost of **conflict resolution** and weaker consistency guarantees).
</v-click><v-click>

We discussed issues arising from **replication lag**, and some **consistency models**
that can help decide how our application (or certain workflows in our application) should behave under replication lag.
</v-click><v-click>

Lastly was a brief look at how replicas in multi-leader and leaderless configurations
eventually **converge** to a consistent state by detecting **concurrent writes** and
using a _conflict resolution algorithm_.
</v-click>

---

:: title ::

## Practical Takeaways

:: content ::

Some common ways teams use _MySQL_ replicas for read workflows:

<div class="ns-c-tight">
<v-clicks class='ns-c-fader'>

- **"Stale-ok" read offloading** (the default win): sometimes being behind a few seconds is acceptable -- search/autocomplete results, non-critical counters/badges, product listings, content pages; we might define a _staleness budget_ (this endpoint tolerates 5s lag)
- **Read-after-write workflows**: A) Session stickiness - after each write
  route the user/session to primary for $N$ seconds; B) Lag-aware routing - use
  replica only if lag $\lt$ threshold; C) Causal reads - capture transaction
  position (_GTID_) after a write and ensure next read is from replica that has
  applied up to that point
- **Workload isolation**: dedicated replicas for specific _read heavy_ workloads
  -- reporting/dashboards, admin tools, batch jobs (exports, reconciliation),
  etc.
- **Replica-driven pipelines**: use replicas for downstream systems -- search
  indexers, cache warmers, ETL to warehouse, audit streams, change consumers
- **Safety patterns**: A) Hot standby - keep replica out of _LB_; best chance of
  being healthy and can be used for failovers; B) Delayed replica - run a
  replica with intentional delay (e.g. 30 minutes) to protect against accidental
  deletes/updates ("undo button")

</v-clicks>
</div>

---

:: title ::

## Practical Takeaways

:: content ::

<div class="flex flex-wrap">
<div class="w-4/10">

Some rules of thumb when using replicas:

<div class='ns-c-tight'>
<v-clicks class='ns-c-fader'>

- Don't run **locking reads** (`SELECT ... FOR UPDATE`/`FOR SHARE`) on replicas
  for correctness
- Avoid "read from any replica" for multi-step UX flows unless you ensure
  **monotonic reads**

</v-clicks>
</div>
</div>
<div class="w-1/10"></div>
<div class="w-4/10">

<v-click>

We can classify reads into ==3 tiers==:

</v-click>
<div class='ns-c-tight'>
<v-clicks class='ns-c-fader'>

- **Strong** (must be fresh): ==primary==; checkout state, immediately-after-write
  reads
- **Causal** (must include my last write): ==stickiness or wait-for-GTID==; profile
  update then view, post then view, settings then reload
- **Eventual** (stale-ok): feeds, browse, public pages, search, dashboards

</v-clicks>
</div>
</div>
</div>

---

:: title ::

## Case Study: Infra Center

:: content ::

Here are some example workflows/endpoints in _Infra Center_ that might benefit
from a read replica:

<div class="ns-c-tight">
<v-clicks class='ns-c-fader'>

- **Browse Servers**: search servers with filters such as `IDC`, `Region`, `Brand`; moderately sized table, many joins, definitely read heavy (tops our slowlogs)
- **Export Servers**: export as CSV/Excel with aforementioned filters; can be
  essentially a full table scan
- **Browse/Export Network Devices**: similar to servers; slightly less complex
- **Operation Logs**: a `binlog_consumer` inserts _RBR_ events into
  `history_record_tab`; $~100$M rows
- **IDC Power Usage**: ready-heavy aggregation query; needs to scan all assets
  located in a given IDC and fetch their power usage info
- **Celery Workers**

</v-clicks>
</div>

---

:: title ::

## Discussion Questions

:: content ::

<div class="ns-c-tight">
<v-clicks>

1. **Where** do you use replicas today? What's the default routing rule in your
   service?
2. What's the **worst thing** that can happen if a user sees stale data in your
   domain? Annoyance, data corruption, security breach, money loss?
3. How do you **monitor the health** of your replicas? Replication lag, replica
   CPU/IO, "seconds behind source"?
4. Tell us about a **bug caused by replication lag**. How was it diagnosed (logs,
   tracing, comparing primary vs replica) and what was the fix?
5. Where do you have monotonic reads/read-after-write/consistent prefix **requirements** and how do you enforce them?
6. If you run **CDC** / downstream consumers, how do you deal with **schema
   changes**?
7. What queries **scare** you most? Exports, admin search, dashboards, joins on big
   tables?
8. What's one **invariant** you should document for your service? e.g. "this
   endpoint is eventual" or "this flow must be read-your-writes"

</v-clicks>
</div>

---

```yaml
layout: intro
```

# Questions?

Thank you for your attention!

<Cat :size="100" mood="blissful" color="#FDA7DC" v-drag="[29,143,75,75]"/>
