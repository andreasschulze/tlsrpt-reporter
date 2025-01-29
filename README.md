# tlsrpt

The keyword TLSRPT refers to an IETF Standard for SMTP TLS Reporting as defined
in [RFC 8460](https://datatracker.ietf.org/doc/html/rfc8460). SMTP TLS
Reporting standardizes informing other mail platforms of successes and failures
establishing a SMTP TLS session between a sending and a receiving MTA. It helps
to find out if a receiving (e.g. your) platform has issues regarding TLS or if
the sending platform runs into TLS problems (i.e. Machine-in-the-Middle attack,
STARTTLS downgrade) while it tries to establish a TLS protected session with a
receiver.

This project provides a C library and a TLSRPT Reporting Service to assist in
reporting SMTP TLS issues. The [libtlsrpt/REAMDE.md](libtlsrpt) C Library is
meant to be included and used by a MTA in order to send out TLSRPT relevant
datagrams to a TLSRPT Reporting Service. The [tlsrpt/README.md](TLSRPT Reporting
Service) receives, collects, generates and delivers TLSRPT reports.

The tlsrpt project is a joint effort between the
[https://www.postfix.org/](Postfix project), namely Wietse Venema who
co-designed and implemented TLSRPT with the help of `libtlsrpt` into Postfix,
and [https://sys4.de](sys4), who sponsored the project and whose team has put
love and efforts to make this happen.

We want secure communications and we want people to feel free to communicate
whatever they want to about on the Internet. TLSRPT provides the reporting to
create visibilty about issues regarding secure communications. Use it! It's
[LICENSE](free).

Start a discussion or create a ticket on GitHub if you have specific questions
about the software provided by the project and / or join the
[https://list.sys4.de/postorius/lists/tlsrpt.list.sys4.de/](TLSRPT mailing list)
for general discussions on TLSRPT but also about this project.

