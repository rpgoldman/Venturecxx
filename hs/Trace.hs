{-# LANGUAGE FlexibleContexts #-}

module Trace where

import qualified Data.Map as M
import Data.Maybe
import Control.Monad.State hiding (state)

import Language hiding (Value, Exp, Env)
import qualified Language as L

-- TODO The version of state that comes from Control.Monad.State on
-- moria appears to have too restrictive a type.
state :: MonadState s m => (s -> (a, s)) -> m a
state action = do
  s <- get
  let (a, s') = action s
  put s'
  return a

type Value = L.Value SPAddress
type Exp = L.Exp Value
type Env = L.Env String Address

newtype Address = Address Int
    deriving (Eq, Ord)

newtype SPAddress = SPAddress Int
    deriving (Eq, Ord)

newtype SRId = SRId Int

data SimulationRequest = SimulationRequest SRId Exp Env

-- TODO An SP needing state of type a takes the a in appropriate
-- places, and offers incorporate and unincorporate functions that
-- transform states.  The Trace needs to contain a heterogeneous
-- collection of all the SP states, perhaps per
-- http://www.haskell.org/haskellwiki/Heterogenous_collections#Existential_types

-- m is presumably an instance of MonadRandom
-- TODO This type signature makes it unclear whether the relevant
-- lists include the operator itself, or just the arguments.
data SP m = SP { requester :: [Address] -> m [SimulationRequest]
               , log_d_req :: Maybe ([Address] -> [SimulationRequest] -> Double)
               , outputter :: [Node] -> [Node] -> m Value
               , log_d_out :: Maybe ([Node] -> [Node] -> Value -> Double)
               }

nullReq :: (Monad m) => a -> m [SimulationRequest]
nullReq _ = return []

trivial_log_d_req :: a -> b -> Double
trivial_log_d_req = const $ const $ 0.0

trivialOut :: (Monad m) => a -> [Node] -> m Value
trivialOut _ (n:_) = return $ fromJust $ valueOf n -- TODO Probably wrong if n is a Reference node
trivialOut _ _ = error "trivialOut expects at least one request result"

compoundSP :: (Monad m) => [String] -> Exp -> Env -> SP m
compoundSP formals exp env =
    SP { requester = req
       , log_d_req = Just $ trivial_log_d_req
       , outputter = trivialOut
       , log_d_out = Nothing
       } where
        -- TODO This requester assumes the operator node is stripped out of the arguments
        req args = return [r] where
            r :: SimulationRequest
            r = SimulationRequest undefined exp $ Frame (M.fromList $ zip formals args) env

data Node = Constant Value
          | Reference Address
          | Request (Maybe [SimulationRequest]) [Address]
          | Output (Maybe Value) [Address] [Address]

valueOf :: Node -> Maybe Value
valueOf (Constant v) = Just v
valueOf (Output v _ _) = v
valueOf _ = Nothing

parentAddrs :: Node -> [Address]
parentAddrs (Constant _) = []
parentAddrs (Reference addr) = [addr]
parentAddrs (Request _ as) = as
parentAddrs (Output _ as as') = as ++ as'

isRegenerated :: Node -> Bool
isRegenerated (Constant _) = True
isRegenerated (Reference addr) = undefined -- TODO: apparently a function of the addressee
isRegenerated (Request Nothing _) = False
isRegenerated (Request (Just _) _) = True
isRegenerated (Output Nothing _ _) = False
isRegenerated (Output (Just _) _ _) = True

----------------------------------------------------------------------
-- Traces
----------------------------------------------------------------------

-- A "torus" is a trace some of whose nodes have Nothing values, and
-- some of whose Request nodes may have outstanding SimulationRequests
-- that have not yet been met.
data Trace rand = 
    Trace { nodes :: (M.Map Address Node)
          , randoms :: [Address]
          , sps :: (M.Map SPAddress (SP rand))
          }

chaseReferences :: Trace rand -> Address -> Maybe Node
chaseReferences t@Trace{ nodes = m } a = do
  n <- M.lookup a m
  chase n
    where chase (Reference a) = chaseReferences t a
          chase n = Just n

parents :: Trace rand -> Node -> [Node]
parents Trace{ nodes = n } node = map (fromJust . flip M.lookup n) $ parentAddrs node

operatorAddr :: Trace rand -> Node -> Maybe SPAddress
operatorAddr t@Trace{ sps = ss } n = do
  a <- op_addr n
  source <- chaseReferences t a
  valueOf source >>= spValue
    where op_addr (Request _ (a:_)) = Just a
          op_addr (Output _ (a:_) _) = Just a
          op_addr _ = Nothing

operator :: Trace rand -> Node -> Maybe (SP rand)
operator t@Trace{ sps = ss } n = operatorAddr t n >>= (flip M.lookup ss)

lookupNode :: Trace rand -> Address -> Maybe Node
lookupNode Trace{ nodes = m } a = M.lookup a m

insertNode :: Address -> Node -> Trace m -> Trace m
insertNode a n t@Trace{nodes = ns} = t{ nodes = (M.insert a n ns) } -- TODO update random choices

addFreshNode :: Node -> Trace m -> (Address, Trace m)
addFreshNode = undefined

addFreshSP :: SP m -> Trace m -> (SPAddress, Trace m)
addFreshSP = undefined

fulfilments :: Address -> Trace m -> [Address]
-- The addresses of the responses to the requests made by the Request
-- node at Address.
fulfilments = undefined

insertResponse :: SPAddress -> SRId -> Address -> Trace m -> Trace m
insertResponse = undefined

lookupResponse :: SPAddress -> SRId -> Trace m -> Maybe Address
lookupResponse = undefined
