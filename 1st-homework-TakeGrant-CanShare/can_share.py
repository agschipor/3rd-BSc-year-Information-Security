import sys
import json



def read_graph(filename):
    try:
        fd = open(filename, "rt")
        graph_json = json.load(fd)
        graph = []
        
        input_data = graph_json["input_data"]

        nodes = graph_json["nodes"]
        for x in range(len(nodes)):
            graph.append([])

        for edge in graph_json["edges"]:
            graph[edge[0]].append((edge[1], edge[2]))

        fd.close()

        return graph, nodes, input_data
    except Exception as e:
        print  e
        return (None, None, None)


def get_islands(graph, nodes):
    islands = []
    undirected_graph = []
    for x in range(len(nodes)):
        islands.append(0)
        undirected_graph.append([])


    for node in range(len(nodes)):
        if nodes[node] != "s":
            continue
        for friend, right in graph[node]:
            if nodes[friend] != 's':
                continue
            if right != 't' and right != 'g':
                continue

            if node not in undirected_graph[friend]:
                undirected_graph[node].append(friend)
                undirected_graph[friend].append(node)
    
    islands_number = 1
    for node in range(len(nodes)):
        if islands[node] == 0 and nodes[node] == "s":
            dfs_islands(node, undirected_graph, nodes, islands, islands_number)
            islands_number += 1
    
    return islands


def dfs_islands(start, graph, nodes, islands, islands_number):
    islands[start] = islands_number

    for friend in graph[start]:
        if islands[friend] == 0:
            dfs_islands(friend, graph, nodes, islands, islands_number)


def get_right_to_node_nodes(graph, r, y):
    xx_nodes = []
    for node in range(len(graph)):
        for friend, right in graph[node]:
            if friend == y and right == r:
                xx_nodes.append(node)

    return xx_nodes


def exists_terminally_span(x, y, graph):
    queue = [x]

    visited = []
    for i in range(len(graph)):
        visited.append(0)

    while queue:
        node = queue.pop(0)

        if visited[node] == 0:
            visited[node] = 1
            t_nodes = []
            for friend, right in graph[node]:
                if right == 't':
                    if friend == y:
                        return True
                    t_nodes.append(friend)
            queue = t_nodes + queue

    return False


def get_terminally_span_nodes(x, graph):
    queue = [x]

    visited = []
    for i in range(len(graph)):
        visited.append(0)

    path = []
    while queue:
        node = queue.pop(0)

        if visited[node] == 0:
            path.append(node)
            visited[node] = 1
            t_nodes = []
            for friend, right in graph[node]:
                if right == 't':
                    t_nodes.append(friend)
            queue = t_nodes + queue

    return path


def get_islands_of_terminally_spans(ry_nodes, graph, nodes, islands, final_node):
    terminally_spans_islands = []
    all_ry_nodes = list(ry_nodes)

    for ry_node in all_ry_nodes:
        if nodes[ry_node] == "s":
            terminally_spans_islands.append(islands[ry_node])
            ry_nodes.remove(ry_node)

    for node in range(len(graph)):
        if node in all_ry_nodes or node == final_node:
            continue
        if nodes[node] != "s":
            continue
        if islands[node] in terminally_spans_islands:
            continue

        terminally_span_nodes = get_terminally_span_nodes(node, graph)
        for ry_node in ry_nodes:
            if ry_node in terminally_span_nodes:
                terminally_spans_islands.append(islands[node])
                break

    return terminally_spans_islands
 

def get_g_terminally_spans(x, graph):
    queue = [x]

    visited = []
    for i in range(len(graph)):
        visited.append(0)

    g_terminally_spans = []
    while queue:
        node = queue.pop(0)

        if visited[node] == 0:
            g_terminally_spans.append(node)
            visited[node] = 1
            t_nodes = []
            for friend, right in graph[node]:
                if right == 't':
                    t_nodes.append(friend)
                elif right == 'g':
                    g_terminally_spans.append(friend)
            queue = t_nodes + queue

    return set(g_terminally_spans)


def get_all_paths(initial_island, islands, initial_node, undirected_graph, path, all_paths, visited, current_island_node):
    for friend in undirected_graph[initial_node]:
        if initial_island == islands[friend]:
            continue

        if visited[friend] == 0:
            visited[friend] = 1
            path.append(friend)
            all_paths.append([current_island_node] + list(path))
            get_all_paths(initial_island, islands, friend, undirected_graph, path, all_paths, visited, current_island_node)
            path.remove(friend)


def is_t_bridge(path, graph):
    length = len(path) - 1
    for index in range(length):
        friend_exists = False
        for friend, right in graph[path[index]]:
            if friend == path[index + 1]:
                if right != "t":
                    return False
                else:
                    friend_exists = True
                    break

        if friend_exists == False:
            return False

    return True


def is_tgt_bridge(path, graph):
    length = len(path) - 1
    
    for index in range(length):
        friend_exists = False
        for friend, right in graph[path[index]]:
            if friend == path[index + 1]:
                if right != "t":
                    if right != "g":
                        return False
                    
                    rev_g_path = []
                    for jindex in reversed(range(index+1, length+1)):
                        rev_g_path.append(path[jindex])

                    return is_t_bridge(rev_g_path, graph)
                else:
                    friend_exists = True
                    break

        if friend_exists == False:
            return False

    return False


def get_bridged_islands(initial_island, islands, graph):
    bridged_islands = []

    undirected_graph = []
    for x in range(len(nodes)):
        undirected_graph.append([])

    for node in range(len(nodes)):
        for friend, right in graph[node]:
            if node not in undirected_graph[friend]:
                undirected_graph[node].append(friend)
                undirected_graph[friend].append(node)

    for ii_node in range(len(graph)):
        if islands[ii_node] != initial_island:
            continue

        visited = []
        for x in range(len(graph)):
            visited.append(0)

        all_paths = []
        get_all_paths(initial_island, islands, ii_node, undirected_graph, [], all_paths, visited, ii_node)
        
        for path in all_paths:
            if islands[path[-1]] == 0:
                continue

            if is_t_bridge(path, graph):
                bridged_islands.append(islands[path[-1]])
            elif is_tgt_bridge(path, graph):
                bridged_islands.append(islands[path[-1]])

            path.reverse()
            if is_t_bridge(path, graph):
                bridged_islands.append(islands[path[0]])
            elif is_tgt_bridge(path, graph):
                bridged_islands.append(islands[path[0]])

    return list(set(bridged_islands))


def exists_bridges(initial_island, terminal_island, islands, graph):
    queue = [initial_island]
    visited = []
    for x in range(len(islands) + 1):
        visited.append(0)

    path = []
    while queue:
        island = queue.pop(0)
        if visited[island] == 0:
            path.append(island)
            print "passed_islands: ", path
            visited[island] = 1
            t_islands = get_bridged_islands(island, islands, graph)
            if terminal_island in t_islands:
                return True
            queue = t_islands + queue

    return False


def can_share(r, x, y, graph_nodes):
    graph = graph_nodes[0]
    nodes = graph_nodes[1]

    for friend, right in graph[x]:
        if friend == y and right == r:
            return True

    islands = get_islands(graph, nodes)

    ry_nodes = get_right_to_node_nodes(graph, r, y)
    print "ry_nodes: ", ry_nodes

    terminally_spans_islands = get_islands_of_terminally_spans(ry_nodes, graph, nodes, islands, y)

    if nodes[x] == "s":
        initially_spans_islands = [islands[x]]
    else:
        gx_nodes = get_right_to_node_nodes(graph, "g", x)
        print "gx_nodes: ", gx_nodes
        initially_spans_islands = get_islands_of_terminally_spans(gx_nodes, graph, nodes, islands, x)

    print "islands: ", islands
    print "initially_spans_islands: ", initially_spans_islands
    print "terminally_spans_islands: ", terminally_spans_islands

    if len(initially_spans_islands) == 0 or len(terminally_spans_islands) == 0:
        return False

    for initially_spans_island in initially_spans_islands:
        for terminally_spans_island in terminally_spans_islands:
            print "current_testing_islands: ", initially_spans_island, terminally_spans_island
            if initially_spans_island == terminally_spans_island:
                return True
            elif exists_bridges(initially_spans_island, terminally_spans_island, islands, graph):
                return True

    return False


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print "Usage: %s <input_file>" % sys.argv[0]
        raise SystemExit

    graph, nodes, input_data = read_graph(sys.argv[1])

    if graph == None or nodes == None or input_data == None:
        raise SystemExit
    
    print "can_share: %s" % can_share(input_data["r"], input_data["x"], input_data["y"], (graph, nodes))