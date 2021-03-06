// Copyright (c) 2014, 2015 MIT Probabilistic Computing Project.
//
// This file is part of Venture.
//
// Venture is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// Venture is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with Venture.  If not, see <http://www.gnu.org/licenses/>.

#ifndef TYPES_H
#define TYPES_H

#include <boost/shared_ptr.hpp>
#include <map>
#include <set>
#include <iostream>
#include <vector>

using boost::shared_ptr;
using boost::dynamic_pointer_cast;
using boost::static_pointer_cast;
using std::vector;
using std::map;
using std::set;
using std::string;
using std::size_t;
using std::pair;
using std::make_pair;
using std::cout;
using std::endl;
using std::flush;

struct VentureValue;
struct Node;
struct ForwardingMap;

typedef int DirectiveID;
typedef boost::shared_ptr<VentureValue> VentureValuePtr;
typedef VentureValuePtr ScopeID;
typedef VentureValuePtr BlockID;
typedef VentureValuePtr FamilyID;
typedef boost::shared_ptr<Node> RootOfFamily;
typedef vector<double> Simplex;
typedef vector<double> Gradient;

/* TODO I keep oscillating on these.
   One convention could be to only use this shortcut for VentureValuePtr.
   Another could be to only use it for all VentureValues, which would include
   SP, Environment, SPRef, and others. */

//typedef shared_ptr<VentureSP> VentureSPPtr;
//typedef shared_ptr<VentureEnvironment> VentureEnvironmentPtr;

#endif
