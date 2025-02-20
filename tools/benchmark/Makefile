#    Copyright (C) 2024-2025 sys4 AG
#    Author Boris Lohner bl@sys4.de
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public
#    License along with this program.
#    If not, see <http://www.gnu.org/licenses/>.

UNAME := $(shell uname)

ifeq ($(UNAME), FreeBSD)
PTHREADCC = -pthread
PTHREADLD = -pthread
else
PTHREADCC =
PTHREADLD = -lpthread
endif


CC=gcc
DEBUG=-g
CFLAGS += -Wall -I ../../../libtlsrpt ${DEBUG} -O2 ${PTHREADCC}
CXXFLAGS += ${CFLAGS} -fpermissive
LDFLAGS += -Wall ${DEBUG} ${PTHREADLD} -lboost_program_options

LDLIBS += ../../../libtlsrpt/.libs/libtlsrpt.a

ifeq ($(UNAME), FreeBSD)
LDLIBS += /lib/libthr.so.3
endif

PROGS = bench bench1
all: ${PROGS}

bench:  $(LDLIBS)
bench1: $(LDLIBS)

clean:
	rm *.o *.a ${PROGS}
