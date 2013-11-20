#ifndef LIST_SPS_H
#define LIST_SPS_H

#include "sp.h"
#include "spaux.h"

struct VenturePair;

struct PairSP : SP
{
  PairSP() { name = "pair"; }
  VentureValue * simulateOutput(const Args & args, gsl_rng * rng) const override;
};

struct FirstSP : SP
{
  FirstSP() { name = "first"; }
  VentureValue * simulateOutput(const Args & args, gsl_rng * rng) const override;
  void flushOutput(VentureValue * value) const override { }
};

struct RestSP : SP
{
  RestSP() { name = "rest"; }
  VentureValue * simulateOutput(const Args & args, gsl_rng * rng) const override;
  void flushOutput(VentureValue * value) const override { }
};

struct ListSP : SP
{
  ListSP() { name = "list"; }
  VentureValue * simulateOutput(const Args & args, gsl_rng * rng) const override;
  void flushOutput(VentureValue * value) const override;
};

struct IsPairSP : SP
{
  IsPairSP() { name = "is_pair"; }
  VentureValue * simulateOutput(const Args & args, gsl_rng * rng) const override;
};


struct ListRefSP : SP
{
  VentureValue * simulateOutput(const Args & args, gsl_rng * rng) const override;
  void flushOutput(VentureValue * value) const override { }
};



// TODO wrap everything in quote
struct MapListSP : SP
{
  MapListSP()
    {
      makesESRs = true;
      canAbsorbRequest = false;
    }
  VentureValue * simulateRequest(const Args & args, gsl_rng * rng) const override;
  void flushRequest(VentureValue * value) const override;
  VentureValue * simulateOutput(const Args & args, gsl_rng * rng) const override;
  void flushOutput(VentureValue * value) const override;

};





#endif
