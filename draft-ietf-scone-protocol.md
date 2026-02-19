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
  DASH:
    title: "Information technology — Dynamic adaptive streaming over HTTP (DASH) — Part 1: Media presentation description and segment formats"
    target: https://www.iso.org/standard/83314.html
    seriesinfo:
      ISO/IEC: 23009-1:2022
    date: 2022-08

--- abstract

This document describes a protocol where on-path network elements
can give endpoints their perspective on what the maximum achievable
throughput might be for QUIC flows.


--- middle

# Introduction

Many networks have known, concrete rate limits, or apply these limits
by policy to constrain data rates.
This is often done without any ability to indicate rate limits to applications.
The result can be that application performance is degraded,
as the manner in which rate limits are enforced can be incompatible with the
rate estimation or congestion control algorithms used at endpoints.

Having the network indicate what its rate limiting policy is, in a way that is
accessible to endpoints, allows applications to use this information when
adapting their send rate.

The Standard Communication with Network Elements (SCONE) protocol
is negotiated by QUIC endpoints.
SCONE provides a means for a network to signal its present best estimate
for maximum sustainable throughput,
or throughput advice,
associated with the flows of UDP datagrams that QUIC exchanges.

Any network function that is able to update the content of UDP datagrams
qualifies as a network element that can use SCONE packets
to provide throughput advice to QUIC endpoints.

Networks with rate limiting policies can use SCONE to send throughput advice
to cooperating endpoints to limit overall network usage.
Where congestion control signals -- such as ECN, delays and loss --
operate on a time scale of a round trip time,
throughput advice operates over a much longer period.

This has benefits in some networks
as endpoints can adapt network usage to better suit network conditions.
For example, radio networks and battery-powered devices
perform better with short, bursty exchanges,
rather than constant transmission at a fixed rate.

For endpoints, SCONE throughput advice makes network policies visible,
which can reduce wasteful probing beyond those limits.


# Overview

QUIC endpoints can negotiate the use of SCONE by including a transport parameter
({{tp}}) in the QUIC handshake.  Endpoints then occasionally send SCONE packets,
which are always coalesced with ordinary QUIC packets that they send.

Networks that have rate limiting policies can detect flows that include
SCONE packets.  The network, via an on-path network element, can indicate a maximum
sustainable throughput by modifying the SCONE packet as it transits the
network element.

The propagation of SCONE packets, including the throughput advice that is added,
is shown in {{f-scone}}.

~~~ aasvg
+--------+    +---------+     +----------+
|  QUIC  |    | Network |     |   QUIC   |
| Sender |    | Element |     | Receiver |
+---+----+    +----+----+     +----+-----+
    |              |               |
    +--- SCONE --->|  SCONE+advice |
    |    +QUIC     +---- +QUIC --->|
    |              |               |  Validate QUIC packet
    |              |               |  and record advice
    |              |               |
~~~
{: #f-scone title="Propagation of SCONE signal"}

QUIC endpoints that receive modified SCONE packets observe the indicated
version, process the QUIC packet, and then record the indicated rate.

Throughput advice only applies to the direction and path for which it is
received.  A connection that migrates or uses multipath
{{?QUIC-MP=I-D.ietf-quic-multipath}}
cannot assume that throughput advice from one path applies to new paths.
Advice for the client-to-server direction and the server-to-client direction of
each path are independent, and are expected to be different, for reasons including
asymmetric link capacity and path diversity.
Applications can use SCONE in either or both directions
of each path as they see fit.


# Applicability

This protocol only works for flows that use the SCONE packet ({{packet}}).

The protocol requires that packets are modified as they transit a
network element, which provides endpoints strong evidence that the network
element has the power to apply a rate limiting policy; though see {{security}} for
potential limitations on this.

The throughput advice that this protocol carries is independent of congestion
signals, limited to a single path and UDP packet flow, unidirectional, and
strictly advisory.

## Independent of Congestion Signals {#not-cc}

SCONE throughput advice is not a substitute for congestion feedback or congestion control.
They are complementary.
Congestion signals,
such as acknowledgments or ECN markings {{?ECN=RFC3168}}{{?WHY-ECN=RFC8087}},
provide information on loss and delay
that indicate the real-time condition of a network path,
whereas SCONE throughput advice operates over a much longer period.

A congestion controller needs to detect changed conditions
and change sending behavior more quickly than SCONE allows for.
Congestion signals can indicate a throughput limit
that is different from the signaled throughput advice.

Endpoints cannot assume that the rate indicated in throughput advice is achievable if congestion
signals indicate otherwise.  Congestion could be experienced at a different
point on the network path than the network element that signals throughput advice.
Therefore, endpoints need to respect the send rate constraints that are set by a
congestion controller.

Networks can use SCONE to communicate throughput advice
for reasons other than rate limiting policies.
For example, a network element in an access network
could provide reduced throughput advice
to guide application use of network capacity
during periods of unusually high usage.

In addition to rate limiting policies,
throughput advice can indicate temporary increases in available capacity
or temporarily reduced capacity.
This includes persistent overuse, equipment faults, or other transient issues.
Providing advice is applicable if increases or reductions
are expected to last for more than one monitoring period; see {{time}}.


## Unspecified Scope

Modifying a packet does not prove that the throughput that is indicated
would be achievable.
A signal that is sent for a specific flow
could apply to a collection of flows,
rather than a single flow.
The scope of the flows that are included is not carried in the signal.

For instance, policy limits might apply at a network subscription level,
such that multiple flows receive the same signal
and combined usage contributes to the shared limit.

Endpoints can therefore be more confident in the throughput signal
as an indication of the maximum achievable throughput
than as any indication of expected throughput.
In addition to endpoints respecting congestion signals (see {{not-cc}}),
networks might need to monitor and enforce policies,
even where applications attempt to follow advice (see {{policing}}).

The advised throughput will likely only be achievable
when the application is the only user of throughput
within the scope that the advice applies to.
In the presence of multiple flows,
achievable throughput could be lower
than what is indicated by the advice,
with throughput determined by a congestion controller.

This implies that signals can most usefully be applied to a downlink flow
in access networks, close to an endpoint. In that case, capacity is less likely
to be split between multiple active flows.

## Per-Flow Signal

The same address tuple
(IP version, source and destination IP addresses and UDP ports)
might be used for multiple QUIC connections.
A single signal might be lost
or only reach a single application endpoint.
Network elements can apply SCONE advice
to all QUIC connections that include SCONE packets
to ensure that advice is received by all application endpoints.

The signaled advice applies to the flow of packets
on the same address tuple for the duration of
the current monitoring period, unless it is updated
earlier or the flow ends; see {{time}} for details on
the monitoring period.

Rate limiting policies often apply on the level of a device or subscription,
but endpoints cannot assume that this is the case.
A separate signal can be sent for each flow.

Network elements that apply throughput advice to a flow
that provides an encrypted tunnel for an encapsulated flow
(such as {{?CONNECT-UDP=RFC9298}})
only applies to the outermost flow.
Advice can be applied on flows that are subsequently encapsulated,
but following that advice can have security implications;
see {{active-attacks}}.


## Unidirectional Signal

Throughput advice is signaled with SCONE packets
that are transmitted as part of the flow that the advice applies to.
Carrying signals in the affected flow,
in the same way that ECN signals are conveyed,
ensures that there is no ambiguity about what flow is affected.
However, this means that the endpoint that receives throughput advice
is not the endpoint that needs to adapt its sending behavior.

A receiving endpoint might need to communicate the value it receives
to the sending peer in order to ensure that the limit is respected.
This document does not define how that signaling occurs
as this is specific to the application in use.

## Advisory Signal

Throughput advice indicates what one part of the network
expects to be achievable for flows that transit that portion of the network.
It is possible that very different throughput is achievable --
either higher or lower than the advice --
as determined by congestion control.
Endpoints that receive this signal therefore need to treat the information as advisory.

The fact that an endpoint requests throughput advice does not necessarily mean
that it will adhere to advice; in some cases, the endpoint cannot. For
example, a flow could initially be used to serve video chunks, with the client
selecting appropriate chunks based on received advice, but later switch to a
bulk download for which bitrate adaptation that cannot be similarly controlled. Composite flows
from multiple applications, such as tunneled flows, might only have a subset of
the involved applications that are capable of handling SCONE signals. Therefore,
when a network element detects that throughput exceeds the advertised throughput advice,
it might apply rate limiting.

Network conditions and rate-limit policies can change
in ways that make previously signaled advice obsolete.
For example, routing changes can cause a flow to move to a different network path.
There are no guarantees that updated advice will be sent at such events.


## Application Use of Advice

Applications that choose to follow throughput advice
do so in the way that best suits their needs.

The most obvious way to follow throughput advice is to
inform the sending peer of the advice so that the peer
can adjust send rates as necessary.
This document does not provide specific guidance on how applications
might adapt their use of network capacity in response to advice.

Some applications offer options for rate control
that can offer improved performance when following advice.
For instance, real-time and streaming video applications can often adapt usage.
Typical HTTP Live Streaming {{?HLS=RFC8216}} or DASH {{DASH}}
clients are provided with manifests that allow them to
adjust the bitrate and quality of media segments
based on available network capacity.
Low priority bulk transfer applications, such as software updates,
might also choose to follow advice.

Following throughput advice could
reduce the impact of an application on other network users,
reserves capacity for high-priority activities,
and could avoid potential enforcement action by the network; see {{policing}}.


# Conventions and Definitions

{::boilerplate bcp14-tagged-bcp}


# SCONE Packet {#packet}

A SCONE packet is a QUIC long header packet that follows the QUIC invariants;
see {{Section 5.1 of INVARIANTS}}.

{{fig-scone-packet}} shows the format of the SCONE packet using the conventions
from {{Section 4 of INVARIANTS}}.

~~~ artwork
SCONE Packet {
  Header Form (1) = 1,
  Reserved (1),
  Rate Signal High Bits (6),
  Version (32) = 0x6f7dc0fd or 0xef7dc0fd,
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

The Rate Signal High Bits field consists of the low six bits (0x3f) of the
first byte. Together with the most significant bit of the Version field,
this forms the 7-bit Rate Signal. Values for the Rate Signal are described in
{{rate-signal}}.

The Version field contains either 0x6f7dc0fd or 0xef7dc0fd. The only difference
between these two values is the most significant bit, which also contributes to
the Rate Signal. All other bits are identical, which facilitates detection and
modification of SCONE packets.

This packet includes a Destination Connection ID field that is set to the same
value as other packets in the same datagram; see {{Section 12.2 of QUIC}}.

The Source Connection ID field is set to match the Source Connection ID field of
any packet that follows.  If the next packet in the datagram does not have a
Source Connection ID field, which is the case for packets with a short header
({{Section 5.2 of INVARIANTS}}), the Source Connection ID field is empty
and the Source Connection ID Length field is set to 0.

SCONE packets MUST be included as the first packet in a datagram.
This is primarily to simplify the process of updating throughput advice
in network elements.
This is also necessary in many cases for QUIC versions 1 and 2
because packets with a short header cannot precede any other packets.


## Rate Signals {#rate-signal}

A Rate Signal is a 7-bit unsigned integer (0-127). The high six bits are the
Rate Signal High Bits, and the least significant bit is the most significant
bit of the Version field.

When sent by a QUIC endpoint, the Rate Signal is set to 127.  Receiving a value
of 127 indicates that throughput advice is unknown, either because network
elements on the path are not providing advice or they do not support SCONE. All
other values (0 through 126) represent the ceiling of rates advised by the
network element(s) on the path.

Throughput advice follows a logarithmic scale defined as:

* Base rate (b_min) = 100 Kbps
* Bitrate at value n = b_min * 10^(n/20)

where n is an integer between 0 and 126 represented by the Rate Signal.

{{ex-rates}} lists some of the values for signals
and the corresponding bitrate for each.

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
| Unknown     | 127         |
{: #ex-rates title="Examples of SCONE signals and corresponding rates"}



## Monitoring Period {#time}

The time over which throughput advice applies is defined to be
a period of 67 seconds.

Protocol participants can use a different period,
depending on their role.
Senders can limit their send rate over any time period
up to 67 seconds.
Network elements can monitor and apply limits to send rates
using time period of at least 67 seconds.

The choice of 67 seconds is a compromise between competing interests.
Longer periods allow applications more flexibility
in terms of how to allocate bandwidth over time.
Shorter periods allow networks to administer policies more tightly.
A shorter period also allows applications
to increase send rates sooner
when rates increase.

The choice of 67 seconds, as a prime number,
also helps avoid synchronization with other periodic
effects that are commonly measured in whole seconds.
This includes segment length or key frame intervals in video applications,
but also includes timers for NAT devices; see {{Section 4.3 of ?RFC4787}}.
Any repeating phenomenon at a 67 second interval is therefore
unlikely to be due to other periodic effects.


## Endpoint Processing of SCONE Packets

Processing a SCONE packet involves reading the value from the Rate Signal field.
However, throughput advice MUST be ignored unless another packet from the same
datagram is successfully processed.  Therefore, a SCONE packet always needs to
be coalesced with other QUIC packets.

A SCONE packet is defined by the use of the long header bit (0x80 in the first
byte) and the SCONE protocol version (0x6f7dc0fd or 0xef7dc0fd in the next four
bytes). The 7-bit Rate Signal can be extracted by combining the low 6 bits
of the first byte with the most significant bit of the version field. A SCONE
packet MAY be discarded, along with any packets that come after it in the same
datagram, if the Source Connection ID is not consistent with those coalesced
packets, as specified in {{packet}}.

A SCONE packet is discarded if the rate signal is unknown (127).

A SCONE packet MUST be discarded if the Destination Connection ID does not match
one recognized by the receiving endpoint.

If a connection uses multiple DSCP markings {{!RFC2474}},
the throughput advice that is received on datagrams with one marking
might not apply to datagrams that have different markings.


## Following Throughput Advice {#algorithm}

Endpoints that receive throughput advice can advise their peer of the limit
so that the peer might limit the amount of data it sends
over any monitoring period ({{time}}).
Alternatively, the endpoint might change its own behavior
to effect a similar outcome indirectly,
which might use flow control or changes to request patterns.

An endpoint that receives throughput advice
might receive multiple different values.
If advice is applied by applications,
applications MUST apply the lowest throughput advice
received during any monitoring period; see {{time}}.

After a monitoring period ({{time}})
without receiving throughput advice,
any previous advice expires.
Endpoints can remove any constraints
placed on throughput based on receiving throughput advice.
This does not mean that there are no limits,
either in policy or due to network conditions,
only that these limits are now unknown.
Other constraints on usage will still apply,
which necessarily includes congestion control
and might include other, application-specific constraints.

Allowing advice to expire
ensures that changes in routing
do not cause stale advice to persist indefinitely
when network elements on a new path do not provide advice.

This approach ensures that network elements
are able to reduce the frequency with which they send updated signals
to as low as once per monitoring period.
However, applying signals at a low frequency
risks throughput advice being reset
if no SCONE packet is available for applying signals ({{apply}}),
or the rewritten packets are lost.
Sending the signal multiple times
increases the likelihood that the signal is received.


# Negotiating SCONE {#tp}

A QUIC endpoint indicates that it is able to receive SCONE packets by
including the scone_supported transport parameter (0x219e).

Each endpoint independently indicates willingness to receive SCONE packets.
An endpoint that does not include the scone_supported transport parameter
can send SCONE packets if their peer includes the transport parameter.

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
as the last two bytes of the payload of the UDP datagrams
that commence a new flow, if the protocol permits it.

For example, in QUIC version 1,
these datagrams contain QUIC packets with a long header ({{Section 17.2 of QUIC}}).
The UDP datagrams sent by a client can contain:
one or more QUIC version 1 Initial packets,
zero or more 0-RTT packets,
padding or other data that is discarded on receipt,
and the indication bytes (0xc8, 0x13) as the final bytes of the UDP payload.

This indication MUST be sent in every datagram
until the client receives any datagram from the server,
at which point the client can be confident that the indication was received.

<!--
This indicator is derived from the first two bytes of:
https://martinthomson.github.io/quic-pick/#seed=draft-ietf-scone-protocol-indication;field=version;codepoint=0xc813e2b1
-->

A client that uses a QUIC version that sends length-delimited packets during the handshake,
which includes QUIC versions 1 {{QUIC}} and 2 {{!QUICv2=RFC9369}},
can include an indicator of SCONE support
outside of the QUIC packets at the end of datagrams that start a flow.
The handshakes of these protocols ensures that
the indication can be included in every datagram the client sends
until it receives a response -- of any kind -- from the server.


## Limitations of Indication

This indication does not mean that SCONE signals will be respected,
only that the client is able to negotiate SCONE.
A server might not support SCONE
and either endpoint might choose not to send SCONE packets.
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


# Network Deployment

QUIC endpoints can enable the use of the SCONE protocol
by sending SCONE packets ({{packet}}).
Network elements can then use SCONE and replace
the Rate Signal field ({{apply}})
according to their policies.


## Applying Throughput Advice Signals {#apply}

A network element detects a SCONE packet by observing that a packet has a QUIC
long header and one of the SCONE protocol versions (0x6f7dc0fd or 0xef7dc0fd).

A network element then conditionally replaces the most significant bit of the
Version field and the Rate Signal High Bits field with values of its choosing.

A network element might receive a packet that already includes a rate signal.
The network element replaces the rate signal if it wishes to signal a lower
value for throughput advice;
otherwise, the original values are retained,
preserving the signal from the network element with the lower policy.
A network element MUST NOT replace a rate signal with a higher or unknown value.

The following pseudocode indicates how a network element might detect a SCONE
packet and replace the existing rate signal (`packet_signal`) with a new rate
signal (`target_signal`) that encodes the throughput advice of this network
element.

~~~ pseudocode
is_long = packet[0] & 0x80 == 0x80
packet_version = ntohl(packet[1..5])
if is_long and (packet_version & 0x7fffffff) == SCONE_VERSION_BITS:
  packet_signal = ((packet[0] & 0x3f) << 1) | (packet_version >> 31)
  if target_signal < packet_signal:
    packet[0] = (packet[0] & 0xc0) | (target_signal >> 1)
    packet[1] = (packet[1] & 0x7f) | (target_signal << 7)
~~~

Once the throughput advice is updated,
the network element updates the UDP checksum for the datagram.

To avoid throughput advice expiring,
a network element needs to ensure that it updates throughput advice in SCONE packets
with no more than a monitoring period ({{time}}) between each update.
Because this depends on the availability of SCONE packets
and packet loss can cause signals to be missed,
network elements might need to update more often.
Ideally, network elements update advice in SCONE packets
at least twice per monitoring period,
to match endpoint behavior (see {{extra-packets}}).

At the start of a flow, network elements are encouraged to update the rate
signal of the first few SCONE packets it observes so that endpoints can obtain
throughput advice early.

Senders that send a SCONE packet
or network elements that update SCONE packets
every 20&ndash;30 seconds are likely sufficient to ensure that throughput advice is not lost.
To reduce the risk of synchronization across multiple senders,
which could cause network elements to miss updates,
senders can include a small random delay.

A network element MUST NOT alter datagrams to add SCONE packets
or synthesize datagrams that contain SCONE packets.
The latter will not be accepted and the former,
even if they do not exceed the path MTU as a result,
can be detected by applications and could be ignored.
This document does not define a mechanism to support detection,
but one might be added in future.


## Monitoring Flows {#monitoring}

Providing throughput advice is optional for any network.
A network that updates SCONE packets to provide throughput advice might,
also optionally, choose to monitor flows
to determine whether applications are following advice.

This section outlines a method
that a network element could use
to determine whether advice is being followed.
Network deployments that choose to monitor
are free to follow any monitoring regime that suits their needs.

This monitoring algorithm is guidance only.
However, monitoring any more strictly than the following
could mean that an application
might be incorrectly classified as not following advice.
A looser monitoring approach,
such as monitoring over a longer time window
than the monitoring period (67s)
or using a higher rate than is signaled,
has no risk of incorrect classification.

When a network changes the throughput advice
it intends to provide,
applications need time to adjust their sending behavior.
As a result, any monitoring needs to allow time
for SCONE packets to be updated,
for those packets to be received by endpoints,
and for applications to adapt.

A network element can then monitor affected flows
to determine whether the throughput advice it provided
was followed.

A network element SHOULD base its monitoring
on the maximum value that was configured to apply
during the preceding two monitoring periods.
If the network element cannot update the throughput advice in every SCONE packet
(or can do so only infrequently), a longer period might be used
to account for the possibility that the updated SCONE packets are lost.
This allows applications time to receive advice
and adapt their sending rate.

Any monitoring and policy enforcement could be implemented
in different network elements than the ones that signal throughput advice.
However, network elements MUST NOT enforce throughput based on throughput advice
found in SCONE packets received from other entities, because unlike endpoints,
network elements do not have the capability to validate other QUIC packets
contained in the same datagram; see {{fake-packets}}.


## Flows That Exceed Throughput Advice {#policing}

A network could deploy policy enforcement that drops or delays packets
to ensure that applications do not exceed throughput limits set in policy.

SCONE allows networks to provide advice to applications,
so that stricter limits,
which can be inefficient and lead to worse application performance,
are not necessary in all cases.

Some applications will not support SCONE.
Other applications either will not
or cannot
follow throughput advice.

Networks can monitor flows to determine if applications follow advice;
see {{monitoring}}.
A network could choose to either disable or loosen policy enforcement
for flows where SCONE is active,
but re-enable or tighten enforcement if monitoring indicates
that throughput advice is not being respected.


# Endpoint Usage

The SCONE protocol defines two versions (0x6f7dc0fd and 0xef7dc0fd)
that combined carry throughput advice that covers a range of bitrates
between 100 Kbps and 199.5 Gbps.


## Providing Opportunities to Apply Throughput Advice Signals {#extra-packets}

Endpoints that wish to offer network elements the option to provide throughput advice
signals can send SCONE packets at any time.  This is a decision that a sender
makes when constructing datagrams.

As specified in {{packet}}, when sending SCONE packets, endpoints include the SCONE packet as the first
packet in a datagram, coalesced with additional packets.

Upon confirmation that the peer is willing to receive SCONE packets, an endpoint
SHOULD include SCONE packets in the first few UDP datagrams that it sends. Doing
so increases the likelihood of eliciting early throughput advice from network
elements, allowing applications to apply that advice from the early stages of the
data transfer.

After that, endpoints that seek to receive throughput advice on a flow MUST send
a SCONE packet at least twice each monitoring period; see {{time}}.

Sending SCONE packets more often might be necessary to:

Avoid missing advice:
: If SCONE packets are not sent, updated, and received
  for an entire monitoring period,
  an application might incorrectly assume that no advice is being provided.

Reduce latency:
: The time between SCONE packets determines the maximum delay
  between changes in throughput advice
  and when that advice can be received and acted upon.

A sender can track the receipt of the coalesced QUIC packet
and send another SCONE packet when loss is detected.
However, it is likely simpler to send SCONE packets more often.

Sending a SCONE packet every 20&ndash;30 seconds
is likely sufficient to ensure that throughput advice is not lost,
though endpoints might send a packet every few seconds
to improve responsiveness.
This period could be determined by how quickly an application
is able to respond to a change in throughput advice.

For example, a streaming application
that fetches video segments that are 5 seconds in length
might send SCONE packets on a similar cadence.
A real-time conferencing application might send more often.
In either case, the length of the monitoring period ({{time}})
limits how fast any application needs to react.

Though sending SCONE packets more than once each round trip time
might help reduce exposure to packet loss,
it is better to spread updates over time
rather than to send multiple SCONE packets in less frequent bursts.

The main cost associated with sending SCONE packets
is the reduction in available space in datagrams
for application data.

A network element that wishes to signal updated throughput advice waits for the
next SCONE packet in the desired direction; see {{apply}}.


## Feedback To Sender About Signals {#feedback}

Information about the throughput advice is intended for the sending application.  Any
signal from network elements can be propagated from the receiving application
using an implementation-defined mechanism.

This document does not define a mean for indicating what was received.
The expectation is that any signal is propagated to the application
for handling, and not handled automatically by the transport layer.
How a receiving application communicates throughput advice to a
sending application will depend on the application in use.

Different applications can choose different approaches. For example,
in an application where a receiver drives rate adaptation, it might
not be necessary to define additional signaling.

A sender can use any acknowledgment mechanism provided by the QUIC version in
use to learn whether datagrams containing SCONE packets were likely received.
This might help inform whether to send additional SCONE packets in the event
that a datagram is lost.  For instance, if a UDP datagram carrying both a
SCONE packet and an ack-eliciting QUIC packet is acknowledged, the sender
knows the SCONE packet was also received.  However, rather than relying
solely on transport-layer acknowledgments, an application-layer mechanism
might better indicate what has been received and acted upon.

SCONE packets could be stripped from datagrams in the network, which cannot be
reliably detected.  This could result in a sender falsely believing that no
network element applied throughput advice.
Senders will therefore proceed as though there was no advice.


# Security Considerations {#security}

The modification of packets provides endpoints proof that a network element is
in a position to drop datagrams and could apply a rate limit policy.
{{extra-packets}} states that endpoints only accept signals if the datagram
contains a packet that it accepts to prevent an off-path attacker from inserting
spurious throughput advice.

Some off-path attackers could be able to both
observe traffic and inject packets. Attackers with such capabilities could
observe packets sent by an endpoint, create datagrams coalescing an
arbitrary SCONE packet and the observed packet, and send these datagrams
such that they arrive at the peer endpoint before the original
packet. Spoofed packets that seek to advertise a higher limit
than might otherwise be permitted also need to bypass any
rate limiters. The attacker will thus get arbitrary SCONE packets accepted by
the peer, with the result being that the endpoint receives a false
or misleading rate limit.

The recipient of throughput advice therefore cannot guarantee that
the signal was generated by an on-path network element. However,
the capabilities required of an off-path attacker are substantially
similar to those of on path elements.

The throughput advice is not authenticated.  Throughput advice
might be incorrectly set in order to encourage endpoints to behave in ways that
are not in their interests.  Endpoints are free to ignore limits that they think
are incorrect.  The congestion controller employed by a sender provides
real-time information about the rate at which the network path is delivering
data.

Similarly, if there is a strong need to ensure that throughput advice is respected,
network elements cannot assume that the signaled advice will be respected by
endpoints.

## Fake SCONE Packets {#fake-packets}

Attackers that can inject packets could compose arbitrary "SCONE-like" packets
by selecting a pair of IP addresses and ports, an arbitrary rate signal, a
valid SCONE version number, an arbitrary "destination
connection ID", and an arbitrary "source connection ID".
A coalesced "1RTT" packet will start with
a plausible first octet, and continue with the selected destination connection
ID followed by a sufficiently long series of random bytes, mimicking the
content of an encrypted packet.

Endpoints will reject such packets because they do not contain valid QUIC packets,
but network elements cannot detect this.
All the network elements between the injection point and the destination
will have to process these packets.

Attackers could send a high volume of these "fake" SCONE packets in
a denial of service (DOS) attempt against network elements. The attack will
force the intermediaries to process the fake packets. If network elements
are keeping state for ongoing SCONE flows, this might exhaust memory resources.
The mitigation is the same as for other distributed DOS attacks: limit
the rate of SCONE packets that a network element is willing to process;
possibly, implement logic to distinguish valid SCONE packets from
fake packets; or, use generic protection against Distributed DOS attacks.

Attackers could also try to craft the fake SCONE packets in ways that trigger
a processing error at network elements. For example, they might pick connection
identifiers of arbitrary length. Network elements can mitigate these attacks
with an implementation that fully conforms to the specification of {{packet}}.

## Damage to Other Protocols

Network elements that update SCONE packet fields might do that for datagrams
exchanged in other protocols.
If the first five bytes of the datagram match
the QUIC long header byte and SCONE version,
the network element might modify the signal,
resulting in damage to those protocols.

The most serious damage occurs when every datagram matches
and is subsequently modified,
because that could mean that the protocol is
effectively unable to operate end-to-end.

To that end, network elements MUST only update the content of datagrams
on a given address tuple
a few times each monitoring period.
Network elements MAY update more often
immediately after a change in their throughput advice,
to reduce the reaction time from senders.

In addition, some heuristics might be used
to detect SCONE-compatible QUIC flows.
This includes identification of a QUIC handshake on the flow,
the presence of indications ({{indication}}),
or other heuristics.
If these heuristics indicate a non-QUIC flow,
the safest option is
for network elements to disable updating of datagrams.


# Privacy Considerations {#privacy}

The focus of this analysis is the extent to which observing SCONE
packets could be used to gain information about endpoints.
This might be leaking details of how applications using QUIC
operate or leaks of endpoint identity when using additional
privacy protection, such as a VPN.

Any network element that can observe the content of that packet can read the
throughput advice that was applied.  Any signal is visible on the path, from the point
at which it is applied to the point at which it is consumed at an endpoint.
On path elements can also alter the SCONE signal to try trigger specific
reactions and gain further knowledge.

In the general case of a client connected to a server through the
Internet, we believe that SCONE does not provide much advantage to attackers.
The identities of the clients and servers are already visible through their
IP addresses. Traffic analysis tools already provide more information than
the throughput advice set by SCONE.

There are two avenues of attack that require more analysis:

* that the passive observation of SCONE packets might help identify or
  distinguish endpoints; and
* that active manipulation of SCONE signals might help reveal the
  identity of endpoints that are otherwise hidden behind VPNs or proxies.

## Passive Attacks

If only a few clients and server pairs negotiate the usage of SCONE, the
occasional observation of SCONE packets will "stick out". That observation
could be combined with observation of timing and volume of traffic to
help identify the endpoint or categorize the application that they
are using.

A variation of this issue occurs if SCONE is widely implemented, but
only used in some specific circumstances. In that case, observation of
SCONE packets reveals information about the state of the endpoint.

If multiple servers are accessed through the same front facing server,
Encrypted Client Hello (ECH) can prevent outside parties from
identifying which specific server a client is using. However, if only
a few of these servers use SCONE, any SCONE packets
will help identify which specific server a client is using.

This issue will be mitigated if SCONE becomes widely implemented, and
if the usage of SCONE is not limited to the type of applications
that make active use of the signal.

QUIC implementations are therefore encouraged to make the feature available
unconditionally.  Endpoints might send SCONE packets whenever a peer can accept
them.

## Active Attacks {#active-attacks}

Suppose a configuration in which multiple clients use a VPN or proxy
service to access the same server. The attacker sees the IP addresses
in the packets behind VPN and proxy and also between the users and the VPN,
but it does not know which VPN address corresponds to what user address.

Suppose now that the attacker selects a flow on the link between the
VPN/proxy and server. The attacker applies throughput advice to SCONE packets
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
ECN) signals. There are few reasons to provide per-flow throughput advice in
that situation.  Endpoints might also either disable this feature or ignore any
signals when they are aware of the use of a VPN or proxy.

# IANA Considerations {#iana}

This document registers new QUIC versions ({{iana-version}}) and a QUIC
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
{:compact}

--- back

# Acknowledgments
{:numbered="false"}

{{{Jana Iyengar}}} made significant contributions to the original TRAIN
specification that forms the basis for a large part of this document.
The following people also contributed significantly
to the development of the protocol: {{{Alan Frindell}}},
{{{Gorry Fairhurst}}}, {{{Kevin Smith}}}, and {{{Zaheduzzaman Sarker}}}.
