---
title: "Standard Communication with Network Elements (SCONE) Protocol"
abbrev: "SCONE Protocol"
category: info

docname: draft-ietf-scone-protocol-latest
submissiontype: IETF
number:
date:
consensus: true
v: 3
area: "Web and Internet Transport"
workgroup: SCONE
keyword:
 - locomotive
 - pastry
venue:
  group: "SCONE"
  type: "Working Group"
  mail: "scone@ietf.org"
  arch: "https://mailarchive.ietf.org/arch/browse/scone/"
  github: "ietf-wg-scone/scone"
  latest: "https://ietf-wg-scone.github.io/scone/draft-ietf-scone-protocol.html"

author:
 -
    fullname: Martin Thomson
    organization: Mozilla
    email: mt@lowentropy.net
 -
    fullname: Christian Huitema
    org: Private Octopus Inc.
    email: huitema@huitema.net
 -
    fullname:
      :: 奥 一穂
      ascii: Kazuho Oku
    org: Fastly
    email: kazuhooku@gmail.com
 -
    fullname: Matt Joras
    org: Meta
    email: matt.joras@gmail.com
 -
    fullname: Marcus Ihlar
    org: Ericsson
    email: marcus.ihlar@ericsson.com


normative:
  QUIC: RFC9000
  INVARIANTS: RFC8999

informative:


--- abstract

This document describes a protocol where on-path network elements
can give endpoints their perspective on what the maximum achievable
throughput might be for QUIC flows.


--- middle

# Introduction

Many access networks apply rate limits to constrain the data rate of attached
devices. This is often done without any indication to the applications
running on devices.  The result can be that application performance is degraded,
as the manner in which rate limits are enforced can be incompatible with the
rate estimation or congestion control algorithms used at endpoints.

Having the network indicate what its rate limiting policy is, in a way that is
accessible to endpoints, allows applications to use this information when
adapting their send rate.

Network elements are not limited to communicating information
about rate limiting policies.
Network elements in access networks could provide information
to endpoints that can help account for changes in network capacity
that are not suited to congestion control feedback. This might include
reduced capacity due to overuse, equipment faults, or other transient issues;
conversely, networks might choose to signal increased availability of capacity.

The Standard Communication with Network Elements (SCONE) protocol is
negotiated by QUIC endpoints.  This protocol provides a means for network
elements to signal the maximum available sustained throughput, or rate limits,
for flows of UDP datagrams that transit that network element to a QUIC endpoint.

Networks with rate limiting policies use SCONE to send throughput advice
to cooperating endpoints to limit overall network usage.
Where congestion control signals -- such as ECN, delays and loss --
operate on a time scale of a round trip time,
throughput advice operates over a much longer period.
This has benefits in some networks as endpoints can fully consume
network capacity in bursts,
rather than extending network interaction at lower rates.

For endpoints, SCONE throughput advice makes network policies visible,
which can reduce wasteful probing beyond those limits.


# Overview

QUIC endpoints can negotiate the use of SCONE by including a transport parameter
({{tp}}) in the QUIC handshake.  Endpoints then occasionally coalesce a SCONE
packet with ordinary QUIC packets that they send.

Network elements that have rate limiting policies can detect flows that include
SCONE packets.  The network element can indicate a maximum sustained throughput
by modifying the SCONE packet as it transits the network element.

~~~ aasvg
+--------+    +---------+     +----------+
|  QUIC  |    | Network |     |   QUIC   |
| Sender |    | Element |     | Receiver |
+---+----+    +----+----+     +----+-----+
    |              |               |
    +--- SCONE --->|   SCONE+rate  |
    |    +QUIC     +---- +QUIC --->|
    |              |               |  Validate QUIC packet
    |              |               |  and record rate
    |              |               |
~~~

QUIC endpoints that receive modified SCONE packets observe the indicated
version, process the QUIC packet, and then record the indicated rate.

Indicated rate limits apply only in a single direction.  Separate indications
can be sent for the client-to-server direction and server-to-client direction.
The indicated rates do not need to be the same.

Indicated rate limits only apply to the path on which they are received.  A
connection that migrates or uses multipath {{?QUIC-MP=I-D.ietf-quic-multipath}}
cannot assume that rate limit indications from one path apply to new paths.


# Applicability

This protocol only works for flows that use the SCONE packet ({{packet}}).

The protocol requires that packets are modified as they transit a
network element, which provides endpoints strong evidence that the network
element has the power to apply rate limiting; though see {{security}} for
potential limitations on this.

The throughput advice signal that this protocol carries is independent of congestion
signals, limited to a single path and UDP packet flow, unidirectional, and
strictly advisory.

## Independent of Congestion Signals

Throughput advice signals are not a substitute for congestion feedback.  Congestion
signals, such as acknowledgments, provide information on loss, delay, or ECN
markings {{?ECN=RFC3168}} that indicate the real-time condition of a network
path.  Congestion signals might indicate a throughput that is different from the
signaled rate limit.

Endpoints cannot assume that a signaled rate limit is achievable if congestion
signals indicate otherwise.  Congestion could be experienced at a different
point on the network path than the network element that indicates a rate limit.
Therefore, endpoints need to respect the send rate constraints that are set by a
congestion controller.

## Unspecified Scope

Modifying a packet does not prove that the throughput that is indicated would be
achievable.  A signal that is sent for a specific flow is likely enforced at a
different scope.  The extent of that scope is not carried in the signal.

For instance, limits might apply at a network subscription level, such
that multiple flows receive the same signal.

Endpoints can therefore be more confident in the throughput signal as an
indication of the maximum achievable throughput than as any indication of
expected throughput.  That throughput will only be achievable when there is no
significant data flowing in the same scope.  In the presence of other flows,
congestion limits are likely to determine actual throughput.

This makes the application of signals most usefully applied to a downlink flow
in access networks, close to an endpoint. In that case, capacity is less likely
to be split between multiple active flows.

## Per-Flow Signal

The same UDP address tuple might be used for multiple QUIC connections.  A
single signal might be lost or only reach a single application endpoint.
Network elements that signal about a flow might choose to send additional
signals, using connection IDs to indicate when new connections could be
involved.

## Undirectional Signal

The endpoint that receives a throughput advice signal is not the endpoint that might
adapt its sending behavior as a result of receiving the signal.  This ensures
that the throughput advice signal is attached to the flow that it is mostly likely to
apply to.

An endpoint might need to communicate the value it receives to its peer in order
to ensure that the limit is respected.  This document does not define how that
signaling occurs as this is specific to the application in use.

## Advisory Signal

A signal does not prove that a higher rate would not be successful.  Endpoints
that receive this signal therefore need to treat the information as advisory.

The fact that an endpoint requests bitrate signals does not necessarily mean
that it will adhere to them; in some cases, the endpoint cannot. For
example, a flow may initially be used to serve video chunks, with the client
selecting appropriate chunks based on bitrate signals, but later switch to a
bulk download for which bitrate adaptation is not applicable. Composite flows
from multiple applications, such as tunneled flows, might only have a subset of
the involved applications that are capable of handling SCONE signals. Therefore,
when a network element detects a flow using more bandwidth than advertised via
SCONE, it might switch to applying its policies for non-SCONE flows, using
congestion control signals.

The time and scope over which throughput advice applies is not specified.
Network conditions and rate-limit policies can change in ways that make
previously signaled advice obsolete, and there are no guarantees that
updated advice will be sent at such events. The signaled
advice can be assumed to apply to the flow of packets on the same UDP address
tuple for the duration of that flow.  For rate limiting networks, rate limiting
policies often apply on the level of a device or subscription, but endpoints
cannot assume that this is the case.  A separate signal can be sent for each flow.

## Following Advice

The SCONE throughput advice is advisory (see {{advisory-signal}}).
Applications that chose to follow it will do so in the way that best suits their needs.

The most obvious way to keep within the limits set by throughput advice is to
inform the sending peer of the limit so that the peer can do whatever rate
limiting is necessary.  Alternatively, a receiver can control the release of
flow control credit (see {{Section 4 of QUIC}}) to indirectly limit the sending
rate of a peer.

Some applications offer options for rate control that can offer superior
outcomes.  Real-time and streaming video applications are able to adjust video
quality to fit within a target throughput.  For instance, an HTTP Live Streaming
client {{?HLS=RFC8216}} can ask for lower bitrate, lower quality media segments.


# Conventions and Definitions

{::boilerplate bcp14-tagged-bcp}


# SCONE Packet {#packet}

A SCONE packet is a QUIC long header packet that follows the QUIC invariants
and is compliant with RFC 8999; see {{Section 5.1 of INVARIANTS}}.

{{fig-scone-packet}} shows the format of the SCONE packet using the conventions
from {{Section 4 of INVARIANTS}}.

~~~ artwork
SCONE Packet {
  Header Form (1) = 1,
  Reserved (1),
  Rate Signal (7),
  Common version bits (31) = 0x6f7dc0fd,
  Destination Connection ID Length (8),
  Destination Connection ID (0..2040),
  Source Connection ID Length (8),
  Source Connection ID (0..2040),
}
~~~
{: #fig-scone-packet title="SCONE Packet Format"}

<!--
https://martinthomson.github.io/quic-pick/#seed=draft-ietf-scone-protocol-version;field=version;codepoint=0x6f7dc0fd
Plus https://github.com/ietf-wg-scone/scone/issues/45
-->

The most significant bit (0x80) of the packet indicates that this is a QUIC long
header packet.  The next bit (0x40) is reserved and can be set according to
{{!QUIC-BIT=RFC9287}}.

The Rate Signal field uses 7 bits spanning the low 6 bits (0x3f) of the first
byte and the most significant bit of the version field. This creates a
contiguous 7-bit field with values from 0 to 127. Values for this field are
described in {{rate-signal}}.

The remaining 31 bits of the version field contain the common version bits
0x6f7dc0fd. The complete version field is either 0x6f7dc0fd (when the
least significant bit of the Rate Signal is 0) or 0xef7dc0fd (when the least
significant bit of the Rate Signal is 1). This design facilitates detection
and modification of SCONE packets while maintaining RFC 8999 compliance.

This packet includes a Destination Connection ID field that is set to the same
value as other packets in the same datagram; see {{Section 12.2 of QUIC}}.

The Source Connection ID field is set to match the Source Connection ID field of
any packet that follows.  If the next packet in the datagram does not have a
Source Connection ID field, which is the case for packets with a short header
({{Section 5.2 of INVARIANTS}}), the Source Connection ID field is empty.

SCONE packets SHOULD be included as the first packet in a datagram.  This is
necessary in many cases for QUIC versions 1 and 2 because packets with a short
header cannot precede any other packets.

## Rate Signals {#rate-signal}

The Rate Signal field in SCONE uses 7 bits: the low 6 bits (0x3f) of the first
byte combined with the most significant bit (0x80000000) of the version field.
This creates a contiguous 7-bit field with values from 0 to 127.

When sent by a QUIC endpoint, the Rate Signal field is set to 127, indicating
no rate limit is in place or that the SCONE protocol is not supported by
network elements on the path. All other values (0 through 126) represent the
ceiling of rates being advised by the network element(s) on the path.

The rate limits use a logarithmic scale with:

* Base rate (b_min) = 100 Kbps
* Bitrate at value n = b_min * 10^(n/20)

where n is an integer between 0 and 126 represented by the Rate Signal field.

{{ex-rates}} lists some of the potential values for signals
and the corresponding throughput advice for each.

| Bitrate     | Rate Signal |
|:------------|:------------|
| 100 Kbps    | 0           |
| 112 Kbps    | 1           |
| 126 Kbps    | 2           |
| 141 Kbps    | 3           |
| 1 Mbps      | 20          |
| 1.12 Mbps   | 21          |
| 10 Mbps     | 40          |
| 11.2 Mbps   | 41          |
| 100 Mbps    | 60          |
| 112 Mbps    | 61          |
| 1 Gbps      | 80          |
| 1.12 Gbps   | 81          |
| 10 Gbps     | 100         |
| 11.2 Gbps   | 101         |
| 100 Gbps    | 120         |
| 112 Gbps    | 121         |
| 199.5 Gbps  | 126         |
| No limit    | 127         |
{: #ex-rates title="Examples of SCONE signals and corresponding rates"}


## Endpoint Processing of SCONE Packets

Processing a SCONE packet involves reading the value from the Rate Signal field.
However, this value MUST NOT be used unless another packet from the same
datagram is successfully processed.  Therefore, a SCONE packet always needs to
be coalesced with other QUIC packets.

A SCONE packet is defined by the use of the long header bit (0x80 in the first
byte) and the SCONE protocol version (0x6f7dc0fd or 0xef7dc0fd in the next four
bytes). The 7-bit Rate Signal value can be extracted by combining the low 6 bits
of the first byte with the most significant bit of the version field. A SCONE
packet MAY be discarded, along with any packets that come after it in the same
datagram, if the Source Connection ID is not consistent with those coalesced
packets, as specified in {{packet}}.

A SCONE packet MUST be discarded if the Destination Connection ID does not match
one recognized by the receiving endpoint.

If a connection uses multiple DSCP markings {{!RFC2474}},
the throughput advice that is received on datagrams with one marking
might not apply to datagrams that have different markings.


# Negotiating SCONE {#tp}

A QUIC endpoint indicates that it is willing to receive SCONE packets by
including the scone_supported transport parameter (0x219e).
The scone_supported transport parameter MUST be empty.
Receiving a non-zero length scone_supported transport parameter MUST be treated
as a connection error of type TRANSPORT_PARAMETER_ERROR;
see {{Section 20.1 of QUIC}}.

<!--
https://martinthomson.github.io/quic-pick/#seed=draft-ietf-scone-protocol-tp;field=tp;codepoint=0x219e;size=2
-->

This transport parameter is valid for QUIC versions 1 {{QUIC}} and 2
{{!QUICv2=RFC9369}} and any other version that recognizes the versions,
transport parameters, and frame types registries established in {{Sections 22.2,
22.3, and 22.4 of QUIC}}.


## Indicating Support on New Flows {#indication}

All new flows that are initiated by a client that supports SCONE
MUST include bytes with values 0xc8 and 0x13
as the last two bytes of datagrams
that commence a new flow if the protocol permits it.
This indication MUST be sent in every datagram
until the client receives any datagram from the server,
at which point the client can be confident that the indication was received.

<!--
This indicator is derived from the first two bytes of:
https://martinthomson.github.io/quic-pick/#seed=draft-ietf-scone-protocol-indication;field=version;codepoint=0xc813e2b1
-->

A client that uses a QUIC version that includes length-delimited packets,
which includes QUIC versions 1 {{QUIC}} and 2 {{!QUICv2=RFC9369}},
can include an indicator of SCONE support
at the end of datagrams that start a flow.
The handshakes of these protocols ensures that
the indication can be included in every datagram the client sends
until it receives a response -- of any kind -- from the server.


## Limitations of Indication

This indication does not mean that SCONE signals will be respected,
only that the client is able to negotiate SCONE.
A server might not support SCONE
or might choose not to send SCONE packets.
Finally, applications might be unable to apply throughput advice
or choose to ignore it.

This indication being just two bytes
means that there is a non-negligible risk of collision with other protocols
or even QUIC usage without SCONE indications.
This means that the indication alone is not sufficient to indicate
that a flow is QUIC with the potential for SCONE support.

Despite these limitations,
having an indication might allow network elements to change their starting posture
with respect to their enforcement of their rate limit policies.


## Indications for Migrated Flows

Applications MAY decide to indicate support for SCONE on new flows,
including when migrating to a new path (see {{Section 9 of QUIC}}).
In QUIC version 1 and 2,
the two byte indicator cannot be used.

Sending a SCONE packet for the first few packets on a new path
gives network elements on that path the ability
to recognize the flow as being able to receive throughput advice
and also gives the network element an opportunity to provide that throughput advice.

To enable this indication,
even if an endpoint would not otherwise send SCONE packets,
endpoints can send a SCONE packet
any time they send a QUIC PATH_CHALLENGE or PATH_RESPONSE frame.
This applies to both client and server endpoints,
but only if the peer has sent the transport parameter; see {{tp}}.


# Deployment

QUIC endpoints can enable the use of the SCONE protocol by sending SCONE packets
{{packet}}.  Network elements then apply or replace the Rate Signal field
({{apply}}) according to their policies.


## Applying Throughput Advice Signals {#apply}

A network element detects a SCONE packet by observing that a packet has a QUIC
long header and one of the SCONE protocol versions (0x6f7dc0fd or 0xef7dc0fd).

A network element then conditionally replaces the Version field and the Rate
Signal field with values of its choosing.

A network element might receive a packet that already includes a rate signal.
The network element replaces the rate signal if it wishes to signal a lower
rate limit; otherwise, the original values are retained, preserving the signal
from the network element with the lower policy.

The following pseudocode indicates how a network element might detect a SCONE
packet and replace an existing rate signal,
given throughput advice (`target_throughput`).

~~~ pseudocode
is_long = packet[0] & 0x80 == 0x80
packet_version = ntohl(packet[1..5])
if is_long and (packet_version == SCONE1_VERSION or
                packet_version == SCONE2_VERSION):
  packet_throughput = \
    signal_to_throughput(packet[0] & 0x3f, packet_version)

  if target_throughput < packet_throughput:
    target_signal, target_version = \
      throughput_to_signal(target_throughput)
    packet[0] = packet[0] & 0xc0 | target_signal
    if target_version != packet_version:
      packet[1..5] = htonl(target_version)
~~~

Once the throughput advice signal is updated,
the network element updates the UDP checksum for the datagram.


# Version Interaction {#version-interaction}

The SCONE protocol defines two versions (0x6f7dc0fd and 0xef7dc0fd) that cover
different ranges of bitrates. This design allows for:

*  Support for both very low bitrates (down to 100 Kbps) and very high bitrates
   (up to 199.5 Gbps)
*  Graceful handling of network elements that might only recognize one version.


## Providing Opportunities to Apply Throughput Advice Signals {#extra-packets}

Endpoints that wish to offer network elements the option to add throughout advice
signals can send SCONE packets at any time.  This is a decision that a sender
makes when constructing datagrams. It is recommended that endpoints promptly
send an initial SCONE packet once the peer confirms its willingness to receive
them.

Endpoints MUST send any SCONE packet they send as the first packet in a
datagram, coalesced with additional packets. An endpoint that receives and
discards a SCONE packet without also successfully processing another packet
from the same datagram SHOULD ignore any throughput advice signal. Such a datagram
might be entirely spoofed.

A network element that wishes to signal an updated rate limit waits for the
next SCONE packet in the desired direction.

## Feedback To Sender About Signals {#feedback}

Information about throughout advice is intended for the sending application.  Any
signal from network elements can be propagated to the receiving application
using an implementation-defined mechanism.

This document does not define a means for indicating what was received.
That is, the expectation is that any signal is propagated to the application
for handling, not handled automatically by the transport layer.
How a receiving application communicates the throughput advice signal to a
sending application will depend on the application in use.

Different applications can choose different approaches. For example,
in an application where a receiver drives rate adaptation, it might
not be necessary to define additional signaling.

A sender can use any acknowledgment mechanism provided by the QUIC version in
use to learn whether datagrams containing SCONE packets were likely received.
This might help inform whether to send additional SCONE packets in the event
that a datagram is lost. However, rather than relying on transport signals, an
application might be better able to indicate what has been received and
processed.

SCONE packets could be stripped from datagrams in the network, which cannot be
reliably detected.  This could result in a sender falsely believing that no
network element applied a throughput advice signal.

## Interactions with congestion control

SCONE and congestion control both provide the application with estimates
of a path capacity. They are complementary. Congestion control algorithms
are typically designed to quickly detect and react to congestion, i.e., to
the "minimum" capacity of a path. SCONE informs the endpoint
of the maximum capacity of a path based on network rate limit policy,
network conditions, or a combination of the two.

Consider for example a path in which the bottleneck router implements Early
Congestion Notification as specified in the L4S architecture {{?RFC9330}}.
If the path capacity diminishes, queues will build up and the router
will immediately start increasing the rate at which packets are marked
as "Congestion Experienced". The receiving endpoint will notice these marks,
and inform its peer. The incoming congestion will be detected within
1 round trip time (RTT). This scenario will play out whatever the reason
for the change in capacity, whether due to increased competition between
multiple applications or, for example, to a change in capacity of a wireless
channel.

# Security Considerations {#security}

The modification of packets provides endpoints proof that a network element is
in a position to drop datagrams and could apply a rate limit policy.
{{extra-packets}} states that endpoints only accept signals if the datagram
contains a packet that it accepts to prevent an off-path attacker from inserting
spurious throughput advice signals.

Some off-path attackers may be able to both
observe traffic and inject packets. Attackers with such capabilities could
observe packets sent by an endpoint, create datagrams coalescing an
arbitrary SCONE packet and the observed packet, and send these datagrams
such that they arrive at the peer endpoint before the original
packet. Spoofed packets that seek to advertise a higher limit
than might otherwise be permitted also need to bypass any
rate limiters. The attacker will thus get arbitrary SCONE packets accepted by
the peer, with the result being that the endpoint receives a false
or misleading rate limit.

The recipient of a throughput advice signal therefore cannot guarantee that
the signal was generated by an on-path network element. However,
the capabilities required of an off-path attacker are substantially
similar to those of on path elements.

The actual value of the throughput advice signal is not authenticated.  Any signal
might be incorrectly set in order to encourage endpoints to behave in ways that
are not in their interests.  Endpoints are free to ignore limits that they think
are incorrect.  The congestion controller employed by a sender provides
real-time information about the rate at which the network path is delivering
data.

Similarly, if there is a strong need to ensure that a rate limit is respected,
network elements cannot assume that the signaled limit will be respected by
endpoints.

## Flooding intermediaries with fake packets

Attackers that can inject packets may compose arbitrary "SCONE-like" packets
by selecting a pair of IP addresses and ports, an arbitrary rate signal, a
valid SCONE version number, an arbitrary "destination
connection ID", and an arbitrary "source connection ID". The SCONE packet
will carry these information. A coalesced "1RTT" packet will start with
a plausible first octet, and continue with the selected destination connection
ID followed by a sufficiently long series of random bytes, mimicking the
content of an encrypted packets.

The injected packets will travel towards the destination.
The final destination will reject such packets because the destination ID
is invalid or because decryption fail, but network elements cannot do these checks,
and will have to process the packets. All the network elements between the injection
point and the destination will have to process these packets.

Attackers could send a high volume of these "fake" SCONE packets in
a denial of service (DOS) attempt against network elements. The attack will
force the intermediaries to process the fake packets. If network elements
are keeping state for ongoing SCONE flows, the attack can cause the
excessive allocation of memory resource. The mitigation there
will be the same as mitigation of other distributed DOS attacks: limit
the rate of SCONE packets that a network element is willing to process;
possibly, implement logic to distinguish valid SCONE packets from
fake packets; or, use generic protection against Distributed DOS attacks.

Attackers could also try to craft the fake SCONE packets in ways that trigger
a processing error at network elements. For example, they might pick connection
identifiers of arbitrary length. Network elements can mitigate these attacks
with implementations that fully conform to the specification of {{packet}}.


# Privacy Considerations {#privacy}

The focus of this analysis is the extent to which observing SCONE
packets could be used to gain information about endpoints.
This might be leaking details of how applications using QUIC
operate or leaks of endpoint identity when using additional
privacy protection, such as a VPN.

Any network element that can observe the content of that packet can read the
rate limit that was applied.  Any signal is visible on the path, from the point
at which it is applied to the point at which it is consumed at an endpoint.
On path elements can also alter the SCONE signal to try trigger specific
reactions and gain further knowledge.

In the general case of a client connected to a server through the
Internet, we believe that SCONE does not provide much advantage to attackers.
The identities of the clients and servers are already visible through their
IP addresses. Traffic analysis tools already provide more information than
the data rate limits set by SCONE.

There are two avenues of attack that require more analysis:

* that the passive observation of SCONE packets might help identify or
  distinguish endpoints; and
* that active manipulation of SCONE signals might help reveal the
  identity of endpoints that are otherwise hidden behind VPNs or proxies.

## Passive Attacks

If only few clients and server pairs negotiate the usage of SCONE, the
occasional observation of SCONE packets will "stick out". That observation,
could be combined with observation of timing and volume of traffic to
help identify the endpoint or categorize the application that they
are using.

A variation of this issue occurs if SCONE is widely implemented, but
only used in some specific circumstances. In that case, observation of
SCONE packets reveals information about the state of the endpoint.

If multiple servers are accessed through the same front facing server,
Encrypted Client Hello (ECH) may be used to prevent outside parties to
identify which specific server a client is using. However, if only
a few of these servers use SCONE, any SCONE packets
will help identify which specific server a client is using.

This issue will be mitigated if SCONE becomes widely implemented, and
if the usage of SCONE is not limited to the type of applications
that make active use of the signal.

QUIC implementations are therefore encouraged to make the feature available
unconditionally.  Endpoints might send SCONE packets whenever a peer can accept
them.

## Active Attacks

Suppose a configuration in which multiple clients use a VPN or proxy
service to access the same server. The attacker sees the IP addresses
in the packets behind VPN and proxy and also between the users and the VPN,
but it does not know which VPN address corresponds to what user address.

Suppose now that the attacker selects a flow on the link between the
VPN/proxy and server. The attacker applies throughput advice signals to SCONE packets
in that flow. The attacker chooses a bandwidth that is
lower than the "natural" bandwidth of the connection. A reduction
in the rate of flows between client and VPN/proxy might allow
the attacker to link the altered flow to the client.

~~~ aasvg
+--------+
| Client |------.
+--------+       \      +-------+
                  '---->|       |            +--------+
+--------+              |  VPN  |<==========>|        |
| Client |------------->|   /   |<==========>| Server |
+--------+              | Proxy |<==========>|        |
                  .---->|       |     ^      +--------+
+--------+       /      +-------+     |
| Client |======'                     |
+--------+      ^           Apply throughput advice signal
                 \
                  \
               Observe change
~~~

An attacker that can manipulate SCONE headers can also simulate
congestion signals by dropping packets or by setting the ECN CE bit.
That will also likely result in changes in the congestion response by
the affected client.

A VPN or proxy could defend against this style of attack by removing SCONE (and
ECN) signals. There are few reasons to provide per-flow throughput advice signals in
that situation.  Endpoints might also either disable this feature or ignore any
signals when they are aware of the use of a VPN or proxy.

# IANA Considerations {#iana}

This document registers a new QUIC version ({{iana-version}}) and a QUIC
transport parameter ({{iana-tp}}).


## SCONE Versions {#iana-version}

This document registers the following entries to the "QUIC Versions" registry
maintained at <https://www.iana.org/assignments/quic>, following the guidance
from {{Section 22.2 of QUIC}}.

Value:
: 0x6f7dc0fd

Status:
: permanent

Specification:
: This document

Change Controller:
: IETF (iesg@ietf.org)

Contact:
: QUIC Working Group (quic@ietf.org)

Notes:
: SCONE Protocol - Low Range
{: spacing="compact"}

Value:
: 0xef7dc0fd

Status:
: permanent

Specification:
: This document

Change Controller:
: IETF (iesg@ietf.org)

Contact:
: QUIC Working Group (quic@ietf.org)

Notes:
: SCONE Protocol - High Range
{: spacing="compact"}


## scone_supported Transport Parameter {#iana-tp}

This document registers the scone_supported transport parameter in the "QUIC
Transport Parameters" registry maintained at
<https://www.iana.org/assignments/quic>, following the guidance from {{Section
22.3 of QUIC}}.

Value:
: 0x219e

Parameter Name:
: scone_supported

Status:
: Permanent

Specification:
: This document

Date:
: This date

Change Controller:
: IETF (iesg@ietf.org)

Contact:
: QUIC Working Group (quic@ietf.org)

Notes:
: (none)
{: spacing="compact"}

--- back

# Acknowledgments
{:numbered="false"}

Jana Iyengar has made significant contributions to the original TRAIN
specification that forms the basis for a large part of this document.
