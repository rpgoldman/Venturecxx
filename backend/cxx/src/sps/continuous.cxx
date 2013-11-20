
#include "sp.h"
#include "lkernel.h"
#include "sps/continuous.h"
#include "value.h"

#include <gsl/gsl_rng.h>
#include <gsl/gsl_randist.h>
#include <gsl/gsl_sf.h>

#include <cmath>
#include <vector>

#include <cassert>
#include <iostream>

// LogLikelihoods, from Yura's Utilities.cpp
double NormalDistributionLogLikelihood(double sampled_value, double average, double sigma) {
  double loglikelihood = 0.0;
  loglikelihood -= log(sigma);
  loglikelihood -= 0.5 * log(2.0 * 3.14159265358979323846264338327950);
  double deviation = sampled_value - average;
  loglikelihood -= 0.5 * deviation * deviation / (sigma * sigma);
  return loglikelihood;
}

double GammaDistributionLogLikelihood(double sampled_value, double alpha, double beta) {
  //b^a * x^{a-1} * e^{-b * x} / Gamma(a)
  if (sampled_value <= 0.0) {
    return log(0.0);
  }
  double loglikelihood = alpha * log(beta);
  loglikelihood += (alpha - 1.0) * log(sampled_value);
  loglikelihood -= beta * sampled_value;
  loglikelihood -= gsl_sf_lngamma(alpha);
  return loglikelihood;
}

double InverseGammaDistributionLogLikelihood(double sampled_value, double alpha, double beta) {
  //b^a * x^{-a-1} * e^{-b / x} / Gamma(a)
  double loglikelihood = alpha * log(beta);
  loglikelihood -= (alpha + 1.0) * log(sampled_value);
  loglikelihood -= beta / sampled_value;
  loglikelihood -= gsl_sf_lngamma(alpha);
  return loglikelihood;
}

double BetaDistributionLogLikelihood(double sampled_value, double alpha, double beta) {
  //x^{a-1} * (1-x)^{b-1} / Beta(a, b)
  double loglikelihood = 0.0;
  loglikelihood += (alpha - 1.0) * log(sampled_value);
  loglikelihood += (beta - 1.0) * log(1.0 - sampled_value);
  loglikelihood -= gsl_sf_lnbeta(alpha, beta);
  return loglikelihood;
}

double ChiSquaredDistributionLogLikelihood(double sampled_value, double nu) {
  //(x / 2)^{nu/2 - 1} * e^{-x/2} / (2 * Gamma(nu / 2))
  double loglikelihood = (0.5 * nu - 1.0) * log(0.5 * sampled_value);
  loglikelihood -= 0.5 * sampled_value;
  loglikelihood -= log(2.0);
  loglikelihood -= gsl_sf_lngamma(0.5 * nu);
  return loglikelihood;
}

double InverseChiSquaredDistributionLogLikelihood(double sampled_value, double nu) {
  //(2x)^{-nu/2 - 1} * e^{-1/2x} / (2 * Gamma(nu / 2))
  double loglikelihood = (-0.5 * nu  - 1.0) * log(2.0 * sampled_value);
  loglikelihood -= 0.5 / sampled_value;
  loglikelihood -= log(2.0);
  loglikelihood -= gsl_sf_lngamma(0.5 * nu);
  return loglikelihood;
}

/* Normal */
VentureValue * NormalSP::simulateOutput(const Args & args, gsl_rng * rng)  const
{

  VentureNumber * vmu = dynamic_cast<VentureNumber *>(args.operands[0]);
  VentureNumber * vsigma = dynamic_cast<VentureNumber *>(args.operands[1]);
  assert(vmu);
  assert(vsigma);
  double x = gsl_ran_gaussian(rng, vsigma->x) + vmu->x;
  return new VentureNumber(x);
}

double NormalSP::simulateOutputNumeric(const vector<double> & args, gsl_rng * rng)  const
{
  double x = gsl_ran_gaussian(rng, args[1]) + args[0];
  assert(isfinite(x));
  return x;
}

double NormalSP::logDensityOutput(VentureValue * value, const Args & args)  const
{
  double mu;
  VentureNumber * vmu = dynamic_cast<VentureNumber *>(args.operands[0]);
  if (vmu) { mu = vmu->x; }
  else
  {
    VentureAtom * vcmu = dynamic_cast<VentureAtom*>(args.operands[0]);
    assert(vcmu);
    mu = vcmu->n;
  }

  VentureNumber * sigma = dynamic_cast<VentureNumber *>(args.operands[1]);
  VentureNumber * x = dynamic_cast<VentureNumber *>(value);
  assert(sigma);
  assert(x);
  return NormalDistributionLogLikelihood(x->x, mu, sigma->x);
}

double NormalSP::logDensityOutputNumeric(double output, const vector<double> & args) const
{
  assert(isfinite(args[0]));
  assert(isfinite(args[1]));
  assert(isfinite(output));
  assert(args[1] > 0);
  double ld = NormalDistributionLogLikelihood(output, args[0], args[1]);
  if (!isfinite(ld))
  {
    cout << "Normal(" << args[0] << ", " << args[1] << ") = " << output << " <" << ld << ">" << endl;
  }
  assert(isfinite(ld));
  return ld;
}

vector<ParameterScope> NormalSP::getParameterScopes() const
{
  return {ParameterScope::REAL, ParameterScope::POSITIVE_REAL};
}

vector<double> NormalSP::gradientOfLogDensity(double output,
					      const vector<double> & arguments) const
{
  double mu = arguments[0];
  double sigma = arguments[1];
  double x = output;

  double gradMu = (x - mu) / (sigma * sigma);
  double gradSigma = (((x - mu) * (x - mu)) - (sigma * sigma)) / (sigma * sigma * sigma);
  return { gradMu, gradSigma };
}

/* Gamma */
VentureValue * GammaSP::simulateOutput(const Args & args, gsl_rng * rng)  const
{
  VentureNumber * a = dynamic_cast<VentureNumber *>(args.operands[0]);
  VentureNumber * b = dynamic_cast<VentureNumber *>(args.operands[1]);
  assert(a);
  assert(b);
  double x = gsl_ran_gamma(rng, a->x, 1.0 / b->x);
  return new VentureNumber(x);
}

double GammaSP::logDensityOutput(VentureValue * value, const Args & args)  const
{
  VentureNumber * a = dynamic_cast<VentureNumber *>(args.operands[0]);
  VentureNumber * b = dynamic_cast<VentureNumber *>(args.operands[1]);
  VentureNumber * x = dynamic_cast<VentureNumber *>(value);
  assert(a);
  assert(b);
  assert(x);
  return GammaDistributionLogLikelihood(x->x, a->x, b->x);
}

/* Inverse Gamma */
VentureValue * InvGammaSP::simulateOutput(const Args & args, gsl_rng * rng)  const
{
  VentureNumber * a = dynamic_cast<VentureNumber *>(args.operands[0]);
  VentureNumber * b = dynamic_cast<VentureNumber *>(args.operands[1]);
  assert(a);
  assert(b);
  double x = 1.0 / gsl_ran_gamma(rng, a->x, 1.0 / b->x);
  return new VentureNumber(x);
}

double InvGammaSP::logDensityOutput(VentureValue * value, const Args & args)  const
{
  VentureNumber * a = dynamic_cast<VentureNumber *>(args.operands[0]);
  VentureNumber * b = dynamic_cast<VentureNumber *>(args.operands[1]);
  VentureNumber * x = dynamic_cast<VentureNumber *>(value);
  assert(a);
  assert(b);
  assert(x);
  return InverseGammaDistributionLogLikelihood(x->x, a->x, b->x);
}

/* UniformContinuous */
VentureValue * UniformContinuousSP::simulateOutput(const Args & args, gsl_rng * rng)  const
{
  VentureNumber * a = dynamic_cast<VentureNumber *>(args.operands[0]);
  VentureNumber * b = dynamic_cast<VentureNumber *>(args.operands[1]);
  assert(a);
  assert(b);
  double x = gsl_ran_flat(rng,a->x,b->x);
  return new VentureNumber(x);
}

double UniformContinuousSP::logDensityOutput(VentureValue * value, const Args & args)  const
{
  VentureNumber * a = dynamic_cast<VentureNumber *>(args.operands[0]);
  VentureNumber * b = dynamic_cast<VentureNumber *>(args.operands[1]);
  VentureNumber * x = dynamic_cast<VentureNumber *>(value);
  assert(a);
  assert(b);
  assert(x);
  return log(gsl_ran_flat_pdf(x->x,a->x,b->x));
}

/* Beta */
VentureValue * BetaSP::simulateOutput(const Args & args, gsl_rng * rng)  const
{
  VentureNumber * a = dynamic_cast<VentureNumber *>(args.operands[0]);
  VentureNumber * b = dynamic_cast<VentureNumber *>(args.operands[1]);
  assert(a);
  assert(b);
  double x = gsl_ran_beta(rng,a->x,b->x);
  if (x == 1.0) { x = 0.99; }
  return new VentureNumber(x);
}

double BetaSP::simulateOutputNumeric(const vector<double> & args, gsl_rng * rng) const
{
  assert(args[0] > 0);
  assert(args[1] > 0);
  double x = gsl_ran_beta(rng,args[0],args[1]);
  assert(isfinite(x));
  // TODO FIXME GSL NUMERIC
  if (x == 1.0) { return 0.99; }
  else { return x; }
}

double BetaSP::logDensityOutput(VentureValue * value, const Args & args)  const
{
  VentureNumber * a = dynamic_cast<VentureNumber *>(args.operands[0]);
  VentureNumber * b = dynamic_cast<VentureNumber *>(args.operands[1]);
  VentureNumber * x = dynamic_cast<VentureNumber *>(value);
  assert(a);
  assert(b);
  assert(x);
  return BetaDistributionLogLikelihood(x->x, a->x, b->x);
}

double BetaSP::logDensityOutputNumeric(double output, const vector<double> & args) const
{
  assert(args[0] > 0);
  assert(args[1] > 0);
  assert(0 <= output);
  assert(output <= 1);
  double ld = BetaDistributionLogLikelihood(output, args[0], args[1]);
  if (!isfinite(ld))
  {
    cout << "Beta(" << args[0] << ", " << args[1] << ") = " << output << " <" << ld << ">" << endl;
  }

  assert(isfinite(ld));
  return ld;
}


vector<ParameterScope> BetaSP::getParameterScopes() const
{
  return {ParameterScope::POSITIVE_REAL, ParameterScope::POSITIVE_REAL};
}

vector<double> BetaSP::gradientOfLogDensity(double output,
					      const vector<double> & arguments) const
{
  double a = arguments[0];
  double b = arguments[1];

  double alpha0 = a + b;

  double gradA = log(output) + gsl_sf_psi(alpha0) - gsl_sf_psi(a);
  double gradB = log(output) + gsl_sf_psi(alpha0) - gsl_sf_psi(b);

  return { gradA, gradB };
}

/* Student-t */
VentureValue * StudentTSP::simulateOutput(const Args & args, gsl_rng * rng)  const
{
  VentureNumber * nu = dynamic_cast<VentureNumber *>(args.operands[0]);
  assert(nu);
  double x = gsl_ran_tdist(rng,nu->x);
  return new VentureNumber(x);
}

double StudentTSP::logDensityOutput(VentureValue * value, const Args & args)  const
{
  VentureNumber * nu = dynamic_cast<VentureNumber *>(args.operands[0]);
  VentureNumber * x = dynamic_cast<VentureNumber *>(value);
  assert(nu);
  assert(x);
  return log(gsl_ran_tdist_pdf(x->x,nu->x));
}

VentureValue * ChiSquareSP::simulateOutput(const Args & args, gsl_rng * rng) const
{
  VentureNumber * nu = dynamic_cast<VentureNumber *>(args.operands[0]);
  assert(nu);
  return new VentureNumber(gsl_ran_chisq(rng,nu->x));
}
 
double ChiSquareSP::logDensityOutput(VentureValue * value, const Args & args) const
{
  VentureNumber * nu = dynamic_cast<VentureNumber *>(args.operands[0]);
  VentureNumber * x = dynamic_cast<VentureNumber *>(value);
  assert(nu);
  assert(x);
  return ChiSquaredDistributionLogLikelihood(x->x,nu->x);
}

VentureValue * InverseChiSquareSP::simulateOutput(const Args & args, gsl_rng * rng) const
{
  VentureNumber * nu = dynamic_cast<VentureNumber *>(args.operands[0]);
  assert(nu);
  return new VentureNumber(1.0 / gsl_ran_chisq(rng,nu->x));
}
 
double InverseChiSquareSP::logDensityOutput(VentureValue * value, const Args & args) const
{
  VentureNumber * nu = dynamic_cast<VentureNumber *>(args.operands[0]);
  VentureNumber * x = dynamic_cast<VentureNumber *>(value);
  assert(nu);
  assert(x);
  return InverseChiSquaredDistributionLogLikelihood(x->x,nu->x);
}
