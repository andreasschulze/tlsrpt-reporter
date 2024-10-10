/*
    Copyright (C) 2024 sys4 AG
    Author Boris Lohner bl@sys4.de

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Lesser General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public
    License along with this program.
    If not, see <http://www.gnu.org/licenses/>.
 */

#include <boost/program_options.hpp>
#include <iostream>
#include <math.h>
#include <pthread.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "tlsrpt.h"
#include "duration.h"

using namespace std;
namespace po=boost::program_options;

#define log(...) fprintf(stderr, __VA_ARGS__)

#define SOCKET_NAME "/tmp/tlsrpt-receiver.socket"

// Settings
int secrampup;  // Seconds fo ramp-up to determine base rate as maximum throughput with blocking sockets
int domains; // number of domains for which to report
int forcepol; // 1-15: force one policy combination or 0 to iterate through different policy combinations
int bgthreads; // number of backgroudn threads
int usenewsock; // use new socket for each datagram
int burstwait; // number of seconds to wait between bursts
int maxburst; // maximum number of datagrams in a burst
int maxburstsec; // maximum number of seconds for a burst
int stacksize; // thread stack size

int showrampuperrors=0; // sho error information during ramp up phase
Rate bgrate; // "should" rate of the background threads
int NEWSOCK =0; // Flag to indicate whether we use a new socket each time, will change from 0 to 1 after base rate is measured

// Arrays
Rate *bgrates; // "real" rate of the background threads
int *bgargs; // arguments for the threads: each threads gets its own id as array index
int *bgerrors; // error counts for the threads
pthread_t *threads; // the thread structures

void initialize(int bgthreads) {
  bgrates= new Rate[bgthreads]();
  bgargs= new int[bgthreads]();
  bgerrors= new int[bgthreads]();
  threads= new pthread_t[bgthreads]();
}


// former static macros to open new sockets
#define SOCKOPENINNER if(NEWSOCK) res=tlsrpt_open(&con, SOCKET_NAME); CHECK;
#define SOCKCLOSEINNER if(NEWSOCK) res=tlsrpt_close(&con); CHECK;

// Checker macro to print error information
//#define CHECK if(res!=0) fprintf(stderr, "RESULT AT LINE %d IS %d : %s: %s\n" ,__LINE__, res, tlsrpt_strerror(res), strerror(tlsrpt_errno_from_error_code(res)));
#define CHECK


// sleep for a fitting time period to make current rate c match goal rate g
void ratesleep(const Rate& g, const Rate& c) {
  double d=1/g.rate()-1/c.rate();
  if(d<0) return;
  double next=c.count/g.rate();
  d=next-c.duration();
  timespec ts;
  ts.tv_sec=floor(d);
  ts.tv_nsec=floor((d-ts.tv_sec)*1000000000);
  //cerr<<"Sleep now for "<<ts<<endl;
  nanosleep(&ts, NULL);
}


// send one datagram, the index i determines the set of policies if no fixed set is enforced
int testdatagram(tlsrpt_connection_t *con, int i) {
  int res=0;
  char domain[1024];
  snprintf(domain,1023,"test-%d.example.com",i%domains);
  const char* _reason="Test with unusual characters: °!\"§$%&/()=?`'´\\<|>äöüÄÖÜß";
#define DEBUGSIZE 1024
  char reason[DEBUGSIZE];
  //const char* reason="Test with normal characters: abcdefghijklmnop";
  memset(reason,0,DEBUGSIZE);
  strncpy(reason, _reason, i % (DEBUGSIZE-1));

  tlsrpt_final_result_t polresult=tlsrpt_final_result_t((i/16)%2);

  struct tlsrpt_dr_t *dr=NULL;
  SOCKOPENINNER
    res = tlsrpt_init_delivery_request(&dr, con, domain, "v=TLSRPTv1;rua=mailto:reports@example.com");
  CHECK;

  int pol=forcepol>0?forcepol:(i+(i%16==0?1:0));

  // first policy
  if(pol & 1) {
    res = tlsrpt_init_policy(dr, TLSRPT_POLICY_STS , "company-y.example");
    CHECK;
    res = tlsrpt_add_policy_string(dr,"version: STSv1");
    res = tlsrpt_add_policy_string(dr,"mode: testing");
    res = tlsrpt_add_policy_string(dr,"mx: *.mail.company-y.example");
    res = tlsrpt_add_policy_string(dr,"max_age: 86400");
    CHECK;
    res = tlsrpt_add_mx_host_pattern(dr,"*.mail.company-y.example");
    CHECK;
    res = tlsrpt_add_delivery_request_failure(dr, TLSRPT_STS_POLICY_INVALID, "1.2.3.4", "mailin.example.com", "test-ehlo.example.com", "11.22.33.44", "This is additional information", "999 TEST ERROR");
    CHECK;
    res = tlsrpt_add_delivery_request_failure(dr, TLSRPT_STS_WEBPKI_INVALID, "1.2.3.5", "mailin.example.com", "test-ehlo.example.com", "11.22.33.55", "This is additional information", "999 TEST ERROR");
    CHECK;
    res = tlsrpt_finish_policy(dr,polresult);
    CHECK;
  }

  // second policy
  if(pol & 2) {
    res = tlsrpt_init_policy(dr, TLSRPT_POLICY_TLSA , "company-y.example");
    CHECK;
    res = tlsrpt_add_policy_string(dr,"3 0 1 1F850A337E6DB9C609C522D136A475638CC43E1ED424F8EEC8513D747D1D085D");
    res = tlsrpt_add_policy_string(dr,"3 0 1 12350A337E6DB9C6123522D136A475638CC43E1ED424F8EEC8513D747D1D1234");
    CHECK;
    res = tlsrpt_add_delivery_request_failure(dr, TLSRPT_CERTIFICATE_EXPIRED, "1.2.3.4", "mailin.example.com", "tes-ehlo.example.com", "11.22.33.55", "This is additional information", "999 TEST ERROR");
    CHECK;
    res = tlsrpt_finish_policy(dr,polresult);
  }

  // third policy
  if(pol & 4) {
    res = tlsrpt_init_policy(dr, TLSRPT_NO_POLICY_FOUND , NULL);
    CHECK;
    res = tlsrpt_add_delivery_request_failure(dr, TLSRPT_VALIDATION_FAILURE, "192.168.25.25", NULL, NULL, "11.22.33.55", "Something unexpected happened", "http://www.google.com/");
    CHECK;
    res = tlsrpt_finish_policy(dr,polresult);
  }

  // a policy without failures
  if(pol & 8) {
    res = tlsrpt_init_policy(dr, TLSRPT_POLICY_STS , "company-y.example");
    CHECK;
    res = tlsrpt_add_policy_string(dr,"version: STSv1");
    res = tlsrpt_add_policy_string(dr,"mode: testing and will contain  no failures");
    res = tlsrpt_add_policy_string(dr,"mx: *.mail.company-y.example");
    res = tlsrpt_add_policy_string(dr,"max_age: 86400");
    CHECK;
    res = tlsrpt_add_mx_host_pattern(dr,"*.mail.company-y.example");
    CHECK;
    // intentionally no failures are added here
    res = tlsrpt_finish_policy(dr,polresult);
    CHECK;
  }

  res = tlsrpt_finish_delivery_request(&dr);
  CHECK;

  SOCKCLOSEINNER;
  return res;
}

// backgroudn worker thread, loops to send datagrams at certain rates
void* bgworker(void* arg) {
  tlsrpt_connection_t* con=NULL;
  int res=tlsrpt_open(&con, SOCKET_NAME);
  CHECK;

  int id = *((int*)arg);

  time_t lap = time(NULL);
  int i=0;

  // use two rates, switch every second, have one second warm up pahse and the one second in use
  Rate c;
  Rate n;
  c.start();
  n.start();
  while(true) {
    time_t nlap = time(NULL);
    if(nlap!=lap) { // swap rates so that we are using the warmed up rate
      bgrates[id]=c;
      Rate tmp=c;
      c=n;
      n=tmp;
      n.start();
      lap=nlap;
    }

    c.add(); // add to rate regardless of result, otherwise we would end up in permanent retry on errors
    res=testdatagram(con, i);
    if(res!=0) {
      ++bgerrors[id];
    }
    //cerr<<"BG "<<id<<bgrate<<" vs "<<c<<endl;
    c.stop();
    ratesleep(bgrate,c);
    ++i;
  }
  cerr<<"WORKER TERMINATED?!?"<<endl;
  return NULL;
}


int main(int argc, char *argv[])
{
  po::options_description desc("Allowed options");
  desc.add_options()
    ("help", "produce help message")
    ("threads", po::value<int>(&bgthreads)->default_value(10), "number of background threads")
    ("domains", po::value<int>(&domains)->default_value(1000), "number of different domains to report")
    ("rampup", po::value<int>(&secrampup)->default_value(15), "seconds to run ramp-up phase before determining maximum base rate")
    ("policy", po::value<int>(&forcepol)->default_value(0), "0 for varying mix of policies, 1-15 to always use a fixed set of up to 4 policies")
    ("newsock", po::value<int>(&usenewsock)->default_value(1), "0 to resue existing socket, 1 to use new connection for each datagram")
    ("showrampuperrors", po::value<int>(&showrampuperrors)->default_value(0), "0 to hide ramp up errors, 1 to show them (might flood the screen)")
    ("burstwait", po::value<int>(&burstwait)->default_value(10), "number of seconds to wait between bursts")
    ("maxburst", po::value<int>(&maxburst)->default_value(20000), "maximum number of datagrams in a burst")
    ("maxburstsec", po::value<int>(&maxburstsec)->default_value(2), "maximum number of seconds for a burst")
    ("stacksize", po::value<int>(&stacksize)->default_value(0), "thread stack size, 0 for default")
    ;

  po::variables_map vm;
  po::store(po::parse_command_line(argc, argv, desc), vm);
  po::notify(vm);
  if(vm.count("help")) {
    cout<<desc<<endl;
    return 1;
  }

  cout<<"Parameters are:"<<endl;
  cout<<"secrampup "<<secrampup<<endl;
  cout<<"domains "<<domains<<endl;
  cout<<"forcepol "<<forcepol<<endl;
  cout<<"bgthreads "<<bgthreads<<endl;
  cout<<"usenewsock "<<usenewsock<<endl;
  cout<<"showrampuperrors "<<showrampuperrors<<endl;
  cout<<"burstwait "<<burstwait<<endl;
  cout<<"maxburst "<<maxburst<<endl;
  cout<<"maxburstsec "<<maxburstsec<<endl;
  cout<<"stacksize "<<stacksize<<endl;
  cout<<endl;

  initialize(bgthreads);

  cout<<"Baserate ramp-up phase"<<endl;
  Rate baserate;
  int res=0;
  tlsrpt_connection_t* con=NULL;
  res=tlsrpt_open(&con, SOCKET_NAME);
  CHECK;

  baserate.start();
  time_t rampupstart = time(NULL);
  time_t rampuplastlap = rampupstart;
  int rampuperrors=0;
  int i=0;

  tlsrpt_set_blocking();

  while(true) {
    res=testdatagram(con, i);
    if(res!=0) {
      ++rampuperrors;
    } else {
      baserate.add();
    }
    if(res!=0 && showrampuperrors) {
      fprintf(stderr,"In run %d ",i);
      if(tlsrpt_error_code_is_internal(res)) {
	fprintf(stderr, "Internal library error :  %s\n", tlsrpt_strerror(res));
      } else {
	int e = tlsrpt_errno_from_error_code(res);
	fprintf(stderr,"%s : errno=%d : %s\n", tlsrpt_strerror(res), e, strerror(e));
      }
    }
    time_t now = time(NULL);
    if(now!=rampuplastlap) {
      baserate.stop();
      if(now>=rampupstart+secrampup) break;
      cout<<"Baserate prelim "<<baserate<<" errors:"<<rampuperrors<<endl;
      rampuplastlap=now;
      baserate.start(); // reset counter
    }
    ++i;
  }
  cout<<"Baserate final  "<<baserate<<endl;
  cout<<rampuperrors<<" errors during ramp up"<<endl;

  tlsrpt_set_nonblocking();
  NEWSOCK = usenewsock;

  bgrate = 0.1*baserate;
  // start background threads
  pthread_attr_t attr;
  pthread_attr_init(&attr);
  size_t oldstack;
  pthread_attr_getstacksize(&attr, &oldstack);
  if(stacksize!=0) {
    cout<<"Setting stack size of "<<stacksize<<" instead of "<<oldstack<<endl;
    int res=pthread_attr_setstacksize(&attr, stacksize);
    if(res!=0) {
      cout<<"Could not set stack size! "<<res<<" "<<strerror(res)<<endl;
    }
    size_t newstack;
    pthread_attr_getstacksize(&attr, &newstack);
    cout<<"=>Using stack size of "<<newstack<<" instead of "<<oldstack<<endl;
  } else {
    cout<<"Using default stack size of "<<oldstack<<endl;
  }
  for(i=0; i<bgthreads; ++i) {
    bgargs[i]=i;
    res = pthread_create(&threads[i], &attr, bgworker, &bgargs[i]);
    if(res!=0) {
      cerr<<"Error creating thread "<<i<<" with result "<<res<<" errno "<<errno<<" "<<strerror(errno)<<endl;
    }
  }

  // burst load
  int bi=1;
  while(true) {
    cout<<"Switching bg rate to "<<bi*0.1<<endl;
    bgrate=baserate*(bi*0.1/bgthreads);
    cout<<"Sleep for "<<burstwait<<" seconds"<<endl;
    res = sleep(burstwait);
    if(res!=0) {
      cout<<"Sleep interrupted "<<res<<" errno "<<errno<<" "<<strerror(errno)<<endl;
    }
    Rate burstrate;
    burstrate.start();
    i=0;
    static const clockid_t clk=CLOCK_MONOTONIC;
    struct timespec ts_start;
    struct timespec ts_end;
    clock_gettime(clk,&ts_start);
    while(true) {
      ++i;
      res=testdatagram(con, i);
      if(res==0) burstrate.add();
      clock_gettime(clk,&ts_end);
      double dur=duration(&ts_start, &ts_end);
      if(res!=0 || i>= maxburst || dur>maxburstsec) {
	burstrate.stop();
	cout<<endl<<"Burst "<<burstrate<<" "<<endl;
	if(res!=0) {
	  cerr<<"In run "<<i<<" ";
	  if(tlsrpt_error_code_is_internal(res)) {
	    cerr<<"Internal library error :  "<<tlsrpt_strerror(res);
	  } else {
	    int e = tlsrpt_errno_from_error_code(res);
	    cerr<<tlsrpt_strerror(res)<<" errno="<<e<<" "<<strerror(e);
	  }
	  cerr<<endl;
	}
	Rate totalbg;
	for(int j=0; j<bgthreads; ++j) {
	  cout<<"BG "<<j<<" "<<bgrates[j]<<" errors:"<<bgerrors[j]<<endl;
	  totalbg = (j==0)?bgrates[j]: totalbg + bgrates[j];
	}
	cout<<"BG all "<<totalbg<<endl;
	totalbg = totalbg + burstrate;
	cout<<"Total "<<totalbg<<endl;
	break;
      }
    }
    if(bi==9) {
      bi=1;
    } else {
      bi+=1;
    }
  }

  cerr<<"MAIN TERMINATED?!?"<<endl;
  tlsrpt_close(&con);

  return 0;
}
