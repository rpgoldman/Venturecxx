#include "sps/deterministic.h"
#include "utils.h"
#include "values.h"
#include <cmath>
#include <boost/foreach.hpp>

#include <iostream>
using std::cout;
using std::endl;
VentureValuePtr AddOutputPSP::simulate(shared_ptr<Args> args, gsl_rng * rng) const
{
  VentureValuePtr sum = VentureNumber::makeValue(0);
  for (size_t i = 0; i < args->operandValues.size(); ++i)
  {
    sum = sum+args->operandValues[i];
  }
  return sum;
}

vector<VentureValuePtr> AddOutputPSP::gradientOfSimulate(const shared_ptr<Args> args, const VentureValuePtr value, const VentureValuePtr direction) const {
  vector<VentureValuePtr> grad;
  if(isinstance<VentureNumber>(direction))
  {
    shared_ptr<VentureNumber> direction_number = dynamic_pointer_cast<VentureNumber>(direction);
    assert(direction_number != NULL);
    BOOST_FOREACH(VentureValuePtr val, args->operandValues) 
    {
      grad.push_back(VentureNumber::makeValue(direction_number->getDouble()));
    }
    return grad;
  } 
  else if(isinstance<VentureVector>(direction))
  {
    VectorXd direction_vector = dynamic_pointer_cast<VentureVector>(direction)->getVector();
    double sum = 0;
    for(size_t i = 0; i < direction_vector.size(); i++) 
    {
      sum += direction_vector(i);
    }
    BOOST_FOREACH(VentureValuePtr val, args->operandValues)
    {
      if(isinstance<VentureNumber>(val))
      {
        grad.push_back(VentureNumber::makeValue(sum));
      }
      else if(isinstance<VentureVector>(val))
      {
        grad.push_back(VentureVector::makeValue(direction_vector));
      }
      else
      {
        assert(false);
      }
    }
    return grad;
  }
  else
  {
    throw "unrecognized arg type for gradientOfSimulate of AddOutputPSP";
  }
}


VentureValuePtr SubOutputPSP::simulate(shared_ptr<Args> args, gsl_rng * rng) const
{
  checkArgsLength("minus", args, 2);
  return args->operandValues[0]- args->operandValues[1];
}

VentureValuePtr MulOutputPSP::simulate(shared_ptr<Args> args, gsl_rng * rng) const
{
  VentureValuePtr prod = VentureNumber::makeValue(1);
  for (size_t i = 0; i < args->operandValues.size(); ++i)
  {
    prod = prod*args->operandValues[i];
  }
  return prod;
}

vector<VentureValuePtr> SubOutputPSP::gradientOfSimulate(const shared_ptr<Args> args, const VentureValuePtr value, const VentureValuePtr direction) const {
  vector<VentureValuePtr> grad;
  if(isinstance<VentureNumber>(direction))
  {
    shared_ptr<VentureNumber> direction_number = dynamic_pointer_cast<VentureNumber>(direction);
    assert(direction_number != NULL);
    grad.push_back(VentureNumber::makeValue(direction_number->getDouble()));
    grad.push_back(VentureNumber::makeValue(0-direction_number->getDouble()));
    return grad;
  } 
  else if(isinstance<VentureVector>(direction))
  {
    VectorXd direction_vector = dynamic_pointer_cast<VentureVector>(direction)->getVector();
    grad.push_back(VentureVector::makeValue(direction_vector));
    grad.push_back(VentureVector::makeValue(direction_vector)->neg());
    return grad;
  }
  else
  {
    throw "unrecognized arg type for gradientOfSimulate of SubOutputPSP";
  }
}

vector<VentureValuePtr> MulOutputPSP::gradientOfSimulate(const shared_ptr<Args> args, const VentureValuePtr value, const VentureValuePtr direction) const {
  assert(args->operandValues.size() == 2);
  vector<VentureValuePtr> grad;
  if(isinstance<VentureNumber>(direction))
  {
    shared_ptr<VentureNumber> direction_number = dynamic_pointer_cast<VentureNumber>(direction);
    assert(direction_number != NULL);
    grad.push_back(VentureNumber::makeValue(direction_number->getDouble()*args->operandValues[1]->getDouble()));
    grad.push_back(VentureNumber::makeValue(direction_number->getDouble()*args->operandValues[0]->getDouble()));
    return grad;
  }
  else if(isinstance<VentureVector>(direction))
  {
    VectorXd direction_vector = dynamic_pointer_cast<VentureVector>(direction)->getVector();
    if(isinstance<VentureNumber>(args->operandValues[0]) && isinstance<VentureVector>(args->operandValues[1]))
    {
      double first = args->operandValues[0]->getDouble();
      VectorXd second = args->operandValues[1]->getVector();
      grad.push_back(VentureNumber::makeValue(direction_vector.dot(second)));
      grad.push_back(VentureVector::makeValue(direction_vector*first));
    }
    else if(isinstance<VentureNumber>(args->operandValues[1]) && isinstance<VentureVector>(args->operandValues[0]))
    {
      double second = args->operandValues[1]->getDouble();
      VectorXd first = args->operandValues[0]->getVector();
      grad.push_back(VentureVector::makeValue(direction_vector*second));
      grad.push_back(VentureNumber::makeValue(direction_vector.dot(first)));
    }
    else
    {
      assert(false);
    }
    return grad;
  }
  else
  {
    throw "unrecognized arg type for gradientOfSimulate of MulOutputPSP";
  }  
}

VentureValuePtr DivOutputPSP::simulate(shared_ptr<Args> args, gsl_rng * rng) const
{
  checkArgsLength("divide", args, 2);
  return shared_ptr<VentureNumber>(new VentureNumber(args->operandValues[0]->getDouble() / args->operandValues[1]->getDouble()));
}

VentureValuePtr LogisticOutputPSP::simulate(shared_ptr<Args> args, gsl_rng * rng) const
{
  checkArgsLength("logistic", args, 3);
  VectorXd w = dynamic_pointer_cast<VentureVector>(args->operandValues[0])->getVector();
  VectorXd x = dynamic_pointer_cast<VentureVector>(args->operandValues[1])->getVector();
  double bias = dynamic_pointer_cast<VentureNumber>(args->operandValues[2])->getDouble();
  double z = 1.0/(1+exp(0-w.dot(x)-bias));
  if(z >= 1-1e-8)
    z = z-1e-8;
  else if(z <= 1e-8)
    z = z+1e-8;
  return VentureNumber::makeValue(z);
}

vector<VentureValuePtr> LogisticOutputPSP::gradientOfSimulate(const shared_ptr<Args> args, const VentureValuePtr value, const VentureValuePtr direction) const
{
  checkArgsLength("logistic", args, 3);
  assert(isinstance<VentureNumber>(direction));
  double d = direction->getDouble();
  VectorXd w = dynamic_pointer_cast<VentureVector>(args->operandValues[0])->getVector();
  VectorXd x = dynamic_pointer_cast<VentureVector>(args->operandValues[1])->getVector();
  double bias = dynamic_pointer_cast<VentureNumber>(args->operandValues[2])->getDouble();
  double z = 1.0/(1+exp(0-w.dot(x)-bias));
  vector<VentureValuePtr> grad;
  grad.push_back(VentureVector::makeValue(x*(d*z*(1-z))));
  grad.push_back(VentureVector::makeValue(w*(d*z*(1-z))));
  grad.push_back(VentureNumber::makeValue(d*z*(1-z)));
  return grad;
}

VentureValuePtr IntDivOutputPSP::simulate(shared_ptr<Args> args, gsl_rng * rng) const
{
  checkArgsLength("integer divide", args, 2);
  return shared_ptr<VentureNumber>(new VentureNumber(args->operandValues[0]->getInt() / args->operandValues[1]->getInt()));
}

VentureValuePtr IntModOutputPSP::simulate(shared_ptr<Args> args, gsl_rng * rng) const
{
  checkArgsLength("integer mod", args, 2);
  return shared_ptr<VentureNumber>(new VentureNumber(args->operandValues[0]->getInt() % args->operandValues[1]->getInt()));
}

VentureValuePtr EqOutputPSP::simulate(shared_ptr<Args> args, gsl_rng * rng) const
{
  checkArgsLength("equals", args, 2);
  return shared_ptr<VentureBool>(new VentureBool(args->operandValues[0]->equals(args->operandValues[1])));
}

VentureValuePtr GtOutputPSP::simulate(shared_ptr<Args> args, gsl_rng * rng) const
{
  checkArgsLength(">", args, 2);
  return shared_ptr<VentureBool>(new VentureBool(args->operandValues[0]->getDouble() > args->operandValues[1]->getDouble()));
}

VentureValuePtr GteOutputPSP::simulate(shared_ptr<Args> args, gsl_rng * rng) const
{
  checkArgsLength(">=", args, 2);
  return shared_ptr<VentureBool>(new VentureBool(args->operandValues[0]->getDouble() >= args->operandValues[1]->getDouble()));
}

VentureValuePtr LtOutputPSP::simulate(shared_ptr<Args> args, gsl_rng * rng) const
{
  checkArgsLength("<", args, 2);
  return shared_ptr<VentureBool>(new VentureBool(args->operandValues[0]->getDouble() < args->operandValues[1]->getDouble()));
}

VentureValuePtr LteOutputPSP::simulate(shared_ptr<Args> args, gsl_rng * rng) const
{
  checkArgsLength("<=", args, 2);
  return shared_ptr<VentureBool>(new VentureBool(args->operandValues[0]->getDouble() <= args->operandValues[1]->getDouble()));
}


VentureValuePtr SinOutputPSP::simulate(shared_ptr<Args> args, gsl_rng * rng) const
{
  checkArgsLength("sin", args, 1);
  return shared_ptr<VentureNumber>(new VentureNumber(sin(args->operandValues[0]->getDouble())));
}


VentureValuePtr CosOutputPSP::simulate(shared_ptr<Args> args, gsl_rng * rng) const
{
  checkArgsLength("cos", args, 1);
  return shared_ptr<VentureNumber>(new VentureNumber(cos(args->operandValues[0]->getDouble())));
}


VentureValuePtr TanOutputPSP::simulate(shared_ptr<Args> args, gsl_rng * rng) const
{
  checkArgsLength("tan", args, 1);
  return shared_ptr<VentureNumber>(new VentureNumber(tan(args->operandValues[0]->getDouble())));
}


VentureValuePtr HypotOutputPSP::simulate(shared_ptr<Args> args, gsl_rng * rng) const
{
  checkArgsLength("hypot", args, 2);
  return shared_ptr<VentureNumber>(new VentureNumber(hypot(args->operandValues[0]->getDouble(),args->operandValues[1]->getDouble())));
}

VentureValuePtr ExpOutputPSP::simulate(shared_ptr<Args> args, gsl_rng * rng) const
{
  checkArgsLength("exp", args, 1);
  return shared_ptr<VentureNumber>(new VentureNumber(exp(args->operandValues[0]->getDouble())));
}

VentureValuePtr LogOutputPSP::simulate(shared_ptr<Args> args, gsl_rng * rng) const
{
  checkArgsLength("log", args, 1);
  return shared_ptr<VentureNumber>(new VentureNumber(log(args->operandValues[0]->getDouble())));
}

VentureValuePtr PowOutputPSP::simulate(shared_ptr<Args> args, gsl_rng * rng) const
{
  checkArgsLength("pow", args, 2);
  return shared_ptr<VentureNumber>(new VentureNumber(pow(args->operandValues[0]->getDouble(),args->operandValues[1]->getDouble())));
}

VentureValuePtr SqrtOutputPSP::simulate(shared_ptr<Args> args, gsl_rng * rng) const
{
  checkArgsLength("sqrt", args, 1);
  return shared_ptr<VentureNumber>(new VentureNumber(sqrt(args->operandValues[0]->getDouble())));
}

VentureValuePtr NotOutputPSP::simulate(shared_ptr<Args> args, gsl_rng * rng) const
{
  checkArgsLength("not", args, 1);
  return shared_ptr<VentureBool>(new VentureBool(!args->operandValues[0]->getBool()));
}

VentureValuePtr IsSymbolOutputPSP::simulate(shared_ptr<Args> args, gsl_rng * rng) const
{
  checkArgsLength("is_symbol", args, 1);
  return VentureValuePtr(new VentureBool(dynamic_pointer_cast<VentureSymbol>(args->operandValues[0]) != NULL));
}

VentureValuePtr ToAtomOutputPSP::simulate(shared_ptr<Args> args, gsl_rng * rng) const
{
  checkArgsLength("to_atom", args, 1);
  return VentureValuePtr(new VentureAtom(args->operandValues[0]->getInt()));
}

VentureValuePtr IsAtomOutputPSP::simulate(shared_ptr<Args> args, gsl_rng * rng) const
{
  checkArgsLength("is_atom", args, 1);
  return VentureValuePtr(new VentureBool(dynamic_pointer_cast<VentureAtom>(args->operandValues[0]) != NULL));
}

VentureValuePtr ToRealOutputPSP::simulate(shared_ptr<Args> args, gsl_rng * rng) const
{
  checkArgsLength("to_real", args, 1);
  return VentureNumber::makeValue(args->operandValues[0]->getDouble());
}

VentureValuePtr IsRealOutputPSP::simulate(shared_ptr<Args> args, gsl_rng * rng) const
{
  checkArgsLength("is_real", args, 1);
  return VentureValuePtr(new VentureBool(dynamic_pointer_cast<VentureNumber>(args->operandValues[0]) != NULL));
}
